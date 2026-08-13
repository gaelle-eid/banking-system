import random
from datetime import datetime, timedelta
from decimal import Decimal

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from app.core.database import get_db
from app.core.deps import get_current_user
from app.core.audit import log_action
from app.core.limits import ATM_DAILY_LIMITS_BY_TIER
from app.models.models import Card, Account, Approval, ApprovalEntityType, ApprovalStatus, CardStatus, CardType, CardTier, User
from app.schemas.card import CardRequest, CardOut, CardTierInfoOut, CardTierDetail

router = APIRouter(prefix="/cards", tags=["cards"])


def generate_masked_number() -> str:
    last4 = "".join(str(random.randint(0, 9)) for _ in range(4))
    return f"**** **** **** {last4}"


@router.post("", response_model=CardOut, status_code=201)
async def request_card(
    payload: CardRequest,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(select(Account).where(Account.id == payload.account_id))
    account = result.scalar_one_or_none()
    if not account:
        raise HTTPException(status_code=404, detail="Account not found")
    if account.owner_id != current_user.id:
        raise HTTPException(status_code=403, detail="Not your account")

    if payload.type == CardType.debit:
        existing_result = await db.execute(
            select(Card).where(
                Card.account_id == account.id,
                Card.type == CardType.debit,
                Card.status.in_([CardStatus.pending, CardStatus.active]),
            )
        )
        if existing_result.scalar_one_or_none():
            raise HTTPException(
                status_code=400,
                detail="This account already has a debit card (active or pending). Cancel it first if you need a new one.",
            )

    card = Card(
        account_id=account.id,
        masked_number=generate_masked_number(),
        type=payload.type,
        tier=payload.tier,
        status=CardStatus.pending,
        expiry_date=datetime.utcnow() + timedelta(days=365 * 3),
    )
    db.add(card)
    await db.flush()

    approval = Approval(
        entity_type=ApprovalEntityType.card,
        entity_id=card.id,
        requested_by=current_user.id,
        status=ApprovalStatus.pending,
    )
    db.add(approval)

    await log_action(
        db, current_user.id, "requested", "card", card.id,
        details={"type": payload.type.value, "tier": payload.tier.value},
    )

    await db.commit()
    await db.refresh(card)
    card.account_nickname = account.nickname
    return card


@router.get("/tier-info", response_model=CardTierInfoOut)
async def get_tier_info():
    """Static info on what each card tier gets you - ATM limits (kept in
    sync with the actual enforced limits, not just marketing copy) plus
    the usual real-world comparison points: annual fee, rewards, and
    foreign transaction fee."""
    details = {
        "standard": {
            "annual_fee": Decimal("0"),
            "rewards": "No rewards",
            "foreign_fee": "3%",
            "perks": "No annual fee. Solid everyday card with no frills.",
        },
        "cashback": {
            "annual_fee": Decimal("0"),
            "rewards": "2% cashback on purchases",
            "foreign_fee": "3%",
            "perks": "Earn cashback on purchases, higher ATM limit than Standard.",
        },
        "travel": {
            "annual_fee": Decimal("95"),
            "rewards": "3x points on travel purchases",
            "foreign_fee": "0%",
            "perks": "No foreign transaction fees, travel rewards, higher ATM limit.",
        },
        "premium": {
            "annual_fee": Decimal("250"),
            "rewards": "5% cashback + travel perks",
            "foreign_fee": "0%",
            "perks": "Highest ATM limit, airport lounge access, dedicated support line.",
        },
    }
    return CardTierInfoOut(**{
        tier: CardTierDetail(atm_daily_limit=limit, **details[tier])
        for tier, limit in ATM_DAILY_LIMITS_BY_TIER.items()
    })

@router.get("/me", response_model=list[CardOut])
async def list_my_cards(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(
        select(Card, Account.nickname).join(Account).where(Account.owner_id == current_user.id)
    )
    rows = result.all()
    cards = []
    for card, account_nickname in rows:
        card.account_nickname = account_nickname
        cards.append(card)
    return cards


@router.patch("/{card_id}/cancel", response_model=CardOut)
async def cancel_card(
    card_id: str,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(
        select(Card).join(Account).where(Card.id == card_id, Account.owner_id == current_user.id)
    )
    card = result.scalar_one_or_none()
    if not card:
        raise HTTPException(status_code=404, detail="Card not found")
    if card.status != CardStatus.active:
        raise HTTPException(status_code=400, detail=f"Card is already {card.status.value}")

    card.status = CardStatus.blocked
    await log_action(
        db, current_user.id, "cancelled", "card", card.id,
        details={"masked_number": card.masked_number},
    )
    await db.commit()
    await db.refresh(card)
    return card


@router.patch("/{card_id}/activate", response_model=CardOut)
async def activate_card(
    card_id: str,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Approval by an employee makes a card exist and be technically
    'active', but real cards still require the CLIENT to activate them
    before first use - a fraud-prevention step that proves the card
    reached the right person."""
    result = await db.execute(
        select(Card).join(Account).where(Card.id == card_id, Account.owner_id == current_user.id)
    )
    card = result.scalar_one_or_none()
    if not card:
        raise HTTPException(status_code=404, detail="Card not found")
    if card.status != CardStatus.active:
        raise HTTPException(status_code=400, detail=f"This card is {card.status.value}, not ready to activate")
    if card.activated_at:
        raise HTTPException(status_code=400, detail="This card is already activated")

    card.activated_at = datetime.utcnow()
    await log_action(
        db, current_user.id, "activated", "card", card.id,
        details={"masked_number": card.masked_number},
    )
    await db.commit()
    await db.refresh(card)
    return card


@router.patch("/{card_id}/freeze", response_model=CardOut)
async def freeze_card(
    card_id: str,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Instantly and reversibly lock a card - distinct from cancel, which
    is permanent. The most commonly used card control in real banking apps."""
    result = await db.execute(
        select(Card).join(Account).where(Card.id == card_id, Account.owner_id == current_user.id)
    )
    card = result.scalar_one_or_none()
    if not card:
        raise HTTPException(status_code=404, detail="Card not found")
    if card.status != CardStatus.active:
        raise HTTPException(status_code=400, detail=f"Card is {card.status.value}, cannot freeze")
    if card.frozen:
        raise HTTPException(status_code=400, detail="This card is already frozen")

    card.frozen = True
    await log_action(
        db, current_user.id, "froze", "card", card.id,
        details={"masked_number": card.masked_number},
    )
    await db.commit()
    await db.refresh(card)
    return card


@router.patch("/{card_id}/unfreeze", response_model=CardOut)
async def unfreeze_card(
    card_id: str,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(
        select(Card).join(Account).where(Card.id == card_id, Account.owner_id == current_user.id)
    )
    card = result.scalar_one_or_none()
    if not card:
        raise HTTPException(status_code=404, detail="Card not found")
    if not card.frozen:
        raise HTTPException(status_code=400, detail="This card isn't frozen")

    card.frozen = False
    await log_action(
        db, current_user.id, "unfroze", "card", card.id,
        details={"masked_number": card.masked_number},
    )
    await db.commit()
    await db.refresh(card)
    return card