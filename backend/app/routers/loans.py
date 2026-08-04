from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from app.core.database import get_db
from app.core.deps import get_current_user
from app.models.models import Loan, Approval, ApprovalEntityType, ApprovalStatus, User
from app.schemas.loan import LoanRequest, LoanOut

router = APIRouter(prefix="/loans", tags=["loans"])


@router.post("", response_model=LoanOut, status_code=201)
async def request_loan(
    payload: LoanRequest,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    loan = Loan(
        client_id=current_user.id,
        amount=payload.amount,
        interest_rate=payload.interest_rate,
        term_months=payload.term_months,
    )
    db.add(loan)
    await db.flush()  # get loan.id before commit

    approval = Approval(
        entity_type=ApprovalEntityType.loan,
        entity_id=loan.id,
        requested_by=current_user.id,
        status=ApprovalStatus.pending,
    )
    db.add(approval)

    await db.commit()
    await db.refresh(loan)
    return loan


@router.get("/me", response_model=list[LoanOut])
async def list_my_loans(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(select(Loan).where(Loan.client_id == current_user.id))
    return result.scalars().all()


@router.get("/{loan_id}", response_model=LoanOut)
async def get_loan(
    loan_id: str,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(select(Loan).where(Loan.id == loan_id))
    loan = result.scalar_one_or_none()
    if not loan:
        raise HTTPException(status_code=404, detail="Loan not found")
    if loan.client_id != current_user.id and current_user.role.value == "client":
        raise HTTPException(status_code=403, detail="Not your loan")
    return loan