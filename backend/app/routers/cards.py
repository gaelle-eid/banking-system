import random
from datetime import datetime, timedelta

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from app.core.database import get_db
from app.core.deps import get_current_user
from app.core.audit import log_action
from app.models.models import Card, Account, Approval, ApprovalEntityType, ApprovalStatus, CardStatus, User
from app.schemas.card import CardRequest, CardOut

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

    card = Card(
        account_id=account.id,
        masked_number=generate_masked_number(),
        type=payload.type,
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

    await db.commit()
    await db.refresh(card)
    return card


@router.get("/me", response_model=list[CardOut])
async def list_my_cards(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(
        select(Card).join(Account).where(Account.owner_id == current_user.id)
    )
    return result.scalars().all()


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