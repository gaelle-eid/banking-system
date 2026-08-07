import random
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from app.core.database import get_db
from app.core.deps import get_current_user
from app.core.audit import log_action
from app.models.models import Account, AccountStatus, User
from app.schemas.account import AccountCreate, AccountOut

router = APIRouter(prefix="/accounts", tags=["accounts"])


def generate_account_number() -> str:
    return "".join(str(random.randint(0, 9)) for _ in range(10))


@router.post("", response_model=AccountOut, status_code=status.HTTP_201_CREATED)
async def create_account(
    payload: AccountCreate,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    nickname = payload.nickname
    if not nickname:
        result = await db.execute(
            select(Account).where(
                Account.owner_id == current_user.id,
                Account.type == payload.type,
            )
        )
        existing_count = len(result.scalars().all())
        type_label = payload.type.value.capitalize()
        nickname = f"{type_label} {existing_count + 1}"

    account = Account(
        owner_id=current_user.id,
        account_number=generate_account_number(),
        nickname=nickname,
        type=payload.type,
        currency=payload.currency,
        balance=0,
    )
    db.add(account)
    await db.commit()
    await db.refresh(account)
    return account


@router.get("/me", response_model=list[AccountOut])
async def list_my_accounts(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(select(Account).where(Account.owner_id == current_user.id))
    return result.scalars().all()


@router.get("/{account_id}", response_model=AccountOut)
async def get_account(
    account_id: str,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(select(Account).where(Account.id == account_id))
    account = result.scalar_one_or_none()
    if not account:
        raise HTTPException(status_code=404, detail="Account not found")
    if account.owner_id != current_user.id and current_user.role.value == "client":
        raise HTTPException(status_code=403, detail="Not your account")
    return account


@router.patch("/{account_id}/close", response_model=AccountOut)
async def close_account(
    account_id: str,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    from app.models.models import Card, CardStatus

    result = await db.execute(select(Account).where(Account.id == account_id))
    account = result.scalar_one_or_none()
    if not account:
        raise HTTPException(status_code=404, detail="Account not found")
    if account.owner_id != current_user.id and current_user.role.value == "client":
        raise HTTPException(status_code=403, detail="Not your account")

    if account.balance != 0:
        raise HTTPException(status_code=400, detail="Account must have a zero balance before closing")

    card_result = await db.execute(
        select(Card).where(Card.account_id == account.id, Card.status == CardStatus.active)
    )
    active_card = card_result.scalar_one_or_none()
    if active_card:
        raise HTTPException(
            status_code=400,
            detail="This account has an active card linked to it. Please cancel the card before closing the account.",
        )

    account.status = AccountStatus.closed
    await log_action(
        db, current_user.id, "closed", "account", account.id,
        details={"account_number": account.account_number, "nickname": account.nickname},
    )
    await db.commit()
    await db.refresh(account)
    return account