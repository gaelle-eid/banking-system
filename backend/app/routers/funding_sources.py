import random
from datetime import datetime
from decimal import Decimal

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from app.core.database import get_db
from app.core.deps import get_current_user
from app.core.audit import log_action
from app.models.models import FundingSource, FundingSourceStatus, User
from app.schemas.funding_source import (
    FundingSourceCreate, FundingSourceOut, FundingSourceCreatedOut, FundingSourceVerify,
)

router = APIRouter(prefix="/funding-sources", tags=["funding-sources"])

MAX_VERIFICATION_ATTEMPTS = 3


def _mask(account_number: str) -> str:
    return f"••••{account_number[-4:]}"


def _random_micro_deposit() -> Decimal:
    # Two-decimal amount between $0.01 and $0.99, matching real micro-deposit ranges.
    return Decimal(random.randint(1, 99)) / 100


@router.post("", response_model=FundingSourceCreatedOut, status_code=status.HTTP_201_CREATED)
async def link_funding_source(
    payload: FundingSourceCreate,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Link a new external bank account. It starts unverified - two small
    'micro-deposit' amounts are generated, which the client must enter
    back correctly to prove they control the account. Cannot be used to
    deposit money until verified."""
    amount_1 = _random_micro_deposit()
    amount_2 = _random_micro_deposit()
    while amount_2 == amount_1:
        amount_2 = _random_micro_deposit()

    source = FundingSource(
        user_id=current_user.id,
        bank_name=payload.bank_name,
        masked_account_number=_mask(payload.account_number),
        status=FundingSourceStatus.pending_verification,
        micro_deposit_1=amount_1,
        micro_deposit_2=amount_2,
        verification_attempts=0,
    )
    db.add(source)
    await log_action(
        db, current_user.id, "linked_funding_source", "funding_source", source.id,
        details={"bank_name": payload.bank_name, "masked_account_number": source.masked_account_number},
    )
    await db.commit()
    await db.refresh(source)

    return FundingSourceCreatedOut(
        id=source.id, bank_name=source.bank_name, masked_account_number=source.masked_account_number,
        status=source.status, created_at=source.created_at, verified_at=source.verified_at,
        demo_micro_deposits=[amount_1, amount_2],
    )


@router.get("", response_model=list[FundingSourceOut])
async def list_funding_sources(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(
        select(FundingSource)
        .where(FundingSource.user_id == current_user.id)
        .order_by(FundingSource.created_at.desc())
    )
    return result.scalars().all()


@router.post("/{source_id}/verify", response_model=FundingSourceOut)
async def verify_funding_source(
    source_id: str,
    payload: FundingSourceVerify,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(select(FundingSource).where(FundingSource.id == source_id))
    source = result.scalar_one_or_none()
    if not source:
        raise HTTPException(status_code=404, detail="Funding source not found")
    if source.user_id != current_user.id:
        raise HTTPException(status_code=403, detail="Not your funding source")
    if source.status != FundingSourceStatus.pending_verification:
        raise HTTPException(status_code=400, detail=f"This funding source is already {source.status.value}")

    submitted = {payload.amount_1, payload.amount_2}
    actual = {source.micro_deposit_1, source.micro_deposit_2}

    if submitted == actual:
        source.status = FundingSourceStatus.verified
        source.verified_at = datetime.utcnow()
        await log_action(
            db, current_user.id, "verified_funding_source", "funding_source", source.id,
            details={"bank_name": source.bank_name},
        )
        await db.commit()
        await db.refresh(source)
        return source

    source.verification_attempts = int(source.verification_attempts) + 1
    if int(source.verification_attempts) >= MAX_VERIFICATION_ATTEMPTS:
        source.status = FundingSourceStatus.failed
        await db.commit()
        raise HTTPException(
            status_code=400,
            detail="Too many incorrect attempts. This funding source has been locked - please link it again.",
        )

    await db.commit()
    remaining = MAX_VERIFICATION_ATTEMPTS - int(source.verification_attempts)
    raise HTTPException(
        status_code=400,
        detail=f"Those amounts don't match. You have {remaining} attempt{'s' if remaining != 1 else ''} left.",
    )


@router.delete("/{source_id}", status_code=status.HTTP_204_NO_CONTENT)
async def remove_funding_source(
    source_id: str,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(select(FundingSource).where(FundingSource.id == source_id))
    source = result.scalar_one_or_none()
    if not source:
        raise HTTPException(status_code=404, detail="Funding source not found")
    if source.user_id != current_user.id:
        raise HTTPException(status_code=403, detail="Not your funding source")

    await db.delete(source)
    await log_action(
        db, current_user.id, "removed_funding_source", "funding_source", source.id,
        details={"bank_name": source.bank_name},
    )
    await db.commit()
    return None