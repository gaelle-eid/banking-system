import random

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from app.core.database import get_db
from app.core.deps import get_current_user
from app.models.models import Account, User
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