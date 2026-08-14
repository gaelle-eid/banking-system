from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from decimal import Decimal

from app.core.database import get_db
from app.core.deps import get_current_user
from app.core.audit import log_action
from app.models.models import Loan, LoanStatus, Approval, ApprovalEntityType, ApprovalStatus, Account, Transaction, TransactionType, TransactionStatus, User
from app.schemas.loan import LoanRequest, LoanOut, LoanRepaymentRequest

router = APIRouter(prefix="/loans", tags=["loans"])


@router.post("", response_model=LoanOut, status_code=201)
async def request_loan(
    payload: LoanRequest,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    account_result = await db.execute(select(Account).where(Account.id == payload.disbursement_account_id))
    account = account_result.scalar_one_or_none()
    if not account:
        raise HTTPException(status_code=404, detail="Disbursement account not found")
    if account.owner_id != current_user.id:
        raise HTTPException(status_code=403, detail="You can only receive loan funds into your own account")
    if account.status.value != "active":
        raise HTTPException(status_code=400, detail="This account isn't active")

    loan = Loan(
        client_id=current_user.id,
        amount=payload.amount,
        term_months=payload.term_months,
        purpose=payload.purpose,
        disbursement_account_id=payload.disbursement_account_id,
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

    await log_action(
        db, current_user.id, "requested", "loan", loan.id,
        details={"amount": str(payload.amount), "term_months": payload.term_months, "purpose": payload.purpose},
    )

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


@router.post("/{loan_id}/repay", response_model=LoanOut)
async def make_loan_payment(
    loan_id: str,
    payload: LoanRepaymentRequest,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Make an extra or early payment toward a loan, on top of (or ahead
    of) the regular auto-debited monthly payment."""
    result = await db.execute(select(Loan).where(Loan.id == loan_id))
    loan = result.scalar_one_or_none()
    if not loan:
        raise HTTPException(status_code=404, detail="Loan not found")
    if loan.client_id != current_user.id:
        raise HTTPException(status_code=403, detail="Not your loan")
    if loan.status != LoanStatus.active:
        raise HTTPException(status_code=400, detail=f"This loan is {loan.status.value}, not active")
    if loan.remaining_balance is None or loan.remaining_balance <= 0:
        raise HTTPException(status_code=400, detail="This loan has no remaining balance")

    account_result = await db.execute(select(Account).where(Account.id == loan.disbursement_account_id))
    account = account_result.scalar_one_or_none()
    if not account:
        raise HTTPException(status_code=400, detail="The linked account no longer exists")

    payment = min(payload.amount, loan.remaining_balance)
    if account.balance < payment:
        raise HTTPException(status_code=400, detail="Insufficient funds for this payment")

    account.balance -= payment
    loan.remaining_balance -= payment

    db.add(Transaction(
        account_id=account.id, type=TransactionType.withdrawal,
        amount=payment, status=TransactionStatus.completed,
        initiated_by=current_user.id, source="Loan Repayment (manual)",
    ))

    if loan.remaining_balance <= 0:
        loan.remaining_balance = Decimal("0")
        loan.status = LoanStatus.closed
        loan.next_payment_due = None

    await log_action(
        db, current_user.id, "repaid", "loan", loan.id,
        details={"amount": str(payment), "remaining_balance": str(loan.remaining_balance)},
    )

    await db.commit()
    await db.refresh(loan)
    return loan