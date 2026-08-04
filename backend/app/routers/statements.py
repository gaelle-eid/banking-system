from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from app.core.database import get_db
from app.core.deps import get_current_user
from app.models.models import Statement, Account, User
from app.schemas.statement import StatementOut

router = APIRouter(prefix="/statements", tags=["statements"])


@router.post("/generate/{account_id}", response_model=StatementOut, status_code=201)
async def generate_statement(
    account_id: str,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(select(Account).where(Account.id == account_id))
    account = result.scalar_one_or_none()
    if not account:
        raise HTTPException(status_code=404, detail="Account not found")
    if account.owner_id != current_user.id:
        raise HTTPException(status_code=403, detail="Not your account")

    now = datetime.utcnow()
    period_start = now.replace(day=1, hour=0, minute=0, second=0, microsecond=0)

    statement = Statement(
        account_id=account.id,
        period_start=period_start,
        period_end=now,
    )
    db.add(statement)
    await db.commit()
    await db.refresh(statement)
    return statement


@router.get("/{account_id}", response_model=list[StatementOut])
async def list_statements(
    account_id: str,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(select(Account).where(Account.id == account_id))
    account = result.scalar_one_or_none()
    if not account:
        raise HTTPException(status_code=404, detail="Account not found")
    if account.owner_id != current_user.id:
        raise HTTPException(status_code=403, detail="Not your account")

    result = await db.execute(select(Statement).where(Statement.account_id == account_id))
    return result.scalars().all()