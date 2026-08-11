from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from app.core.database import get_db
from app.core.deps import get_current_user, require_role
from app.core.audit import log_action
from app.models.models import FraudFlag, FraudFlagStatus, Account, AccountStatus, User, UserRole
from app.schemas.fraud import FraudFlagOut, FraudDecisionRequest

router = APIRouter(prefix="/fraud", tags=["fraud"])


@router.get("", response_model=list[FraudFlagOut], dependencies=[Depends(require_role(UserRole.employee, UserRole.admin))])
async def list_fraud_flags(
    status: FraudFlagStatus | None = Query(None),
    db: AsyncSession = Depends(get_db),
):
    query = select(FraudFlag)
    if status:
        query = query.where(FraudFlag.status == status)
    query = query.order_by(FraudFlag.created_at.desc())

    result = await db.execute(query)
    return result.scalars().all()


@router.post("/{flag_id}/clear", response_model=FraudFlagOut, dependencies=[Depends(require_role(UserRole.employee, UserRole.admin))])
async def clear_fraud_flag(
    flag_id: str,
    payload: FraudDecisionRequest,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(select(FraudFlag).where(FraudFlag.id == flag_id))
    flag = result.scalar_one_or_none()
    if not flag:
        raise HTTPException(status_code=404, detail="Flag not found")
    if flag.status != FraudFlagStatus.pending:
        raise HTTPException(status_code=400, detail=f"Flag is already {flag.status.value}")

    flag.status = FraudFlagStatus.cleared
    flag.reviewed_by = current_user.id
    flag.notes = payload.notes

    await log_action(db, current_user.id, "cleared", "fraud_flag", flag.id, details={"notes": payload.notes})
    await db.commit()
    await db.refresh(flag)
    return flag


@router.post("/{flag_id}/confirm-fraud", response_model=FraudFlagOut, dependencies=[Depends(require_role(UserRole.employee, UserRole.admin))])
async def confirm_fraud(
    flag_id: str,
    payload: FraudDecisionRequest,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(select(FraudFlag).where(FraudFlag.id == flag_id))
    flag = result.scalar_one_or_none()
    if not flag:
        raise HTTPException(status_code=404, detail="Flag not found")
    if flag.status != FraudFlagStatus.pending:
        raise HTTPException(status_code=400, detail=f"Flag is already {flag.status.value}")

    flag.status = FraudFlagStatus.confirmed_fraud
    flag.reviewed_by = current_user.id
    flag.notes = payload.notes

    account_result = await db.execute(select(Account).where(Account.id == flag.account_id))
    account = account_result.scalar_one_or_none()
    if account:
        account.status = AccountStatus.frozen

    await log_action(db, current_user.id, "confirmed_fraud", "fraud_flag", flag.id, details={"notes": payload.notes, "account_frozen": True})
    await db.commit()
    await db.refresh(flag)
    return flag