from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from decimal import Decimal
from datetime import datetime, timedelta

from app.core.database import get_db
from app.core.deps import get_current_user, require_role
from app.core.audit import log_action
from app.core.email import send_transaction_email
from app.models.models import (
    Approval, ApprovalStatus, ApprovalEntityType,
    Loan, LoanStatus, Card, CardStatus, Account, Transaction, TransactionType, TransactionStatus,
    User, UserRole,
)
from app.schemas.approval import ApprovalOut, ApprovalActionRequest

router = APIRouter(prefix="/approvals", tags=["approvals"])


@router.get("", response_model=list[ApprovalOut], dependencies=[Depends(require_role(UserRole.employee, UserRole.admin))])
async def list_approvals(
    status: ApprovalStatus | None = Query(None),
    entity_type: ApprovalEntityType | None = Query(None),
    db: AsyncSession = Depends(get_db),
):
    query = select(Approval)
    if status:
        query = query.where(Approval.status == status)
    if entity_type:
        query = query.where(Approval.entity_type == entity_type)
    query = query.order_by(Approval.created_at.desc())

    result = await db.execute(query)
    return result.scalars().all()


@router.post("/{approval_id}/approve", response_model=ApprovalOut, dependencies=[Depends(require_role(UserRole.employee, UserRole.admin))])
async def approve_request(
    approval_id: str,
    payload: ApprovalActionRequest,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(select(Approval).where(Approval.id == approval_id))
    approval = result.scalar_one_or_none()
    if not approval:
        raise HTTPException(status_code=404, detail="Approval not found")
    if approval.status != ApprovalStatus.pending:
        raise HTTPException(status_code=400, detail=f"Approval is already {approval.status.value}")

    if approval.entity_type == ApprovalEntityType.loan:
        loan_result = await db.execute(select(Loan).where(Loan.id == approval.entity_id))
        loan = loan_result.scalar_one_or_none()
        if loan:
            if payload.interest_rate is None:
                raise HTTPException(status_code=400, detail="An interest rate is required to approve a loan")

            disbursement_result = await db.execute(select(Account).where(Account.id == loan.disbursement_account_id))
            disbursement_account = disbursement_result.scalar_one_or_none()
            if not disbursement_account:
                raise HTTPException(status_code=400, detail="The client's disbursement account no longer exists")

            loan.status = LoanStatus.active
            loan.approved_by = current_user.id
            loan.interest_rate = Decimal(str(payload.interest_rate))
            loan.disbursed_at = datetime.utcnow()

            # Simple interest over the full term, split evenly across months.
            rate_decimal = loan.interest_rate / Decimal("100")
            total_interest = loan.amount * rate_decimal * (Decimal(str(loan.term_months)) / Decimal("12"))
            total_repayment = (loan.amount + total_interest).quantize(Decimal("0.01"))
            monthly_payment = (total_repayment / Decimal(str(loan.term_months))).quantize(Decimal("0.01"))

            loan.total_repayment = total_repayment
            loan.monthly_payment = monthly_payment
            loan.remaining_balance = total_repayment
            loan.next_payment_due = datetime.utcnow() + timedelta(days=30)

            disbursement_account.balance += loan.amount
            db.add(Transaction(
                account_id=disbursement_account.id,
                type=TransactionType.deposit,
                amount=loan.amount,
                status=TransactionStatus.completed,
                initiated_by=current_user.id,
                source=f"Loan Disbursement ({loan.term_months}mo @ {loan.interest_rate}%)",
            ))

            client_result = await db.execute(select(User).where(User.id == loan.client_id))
            client = client_result.scalar_one_or_none()
            if client:
                try:
                    send_transaction_email(
                        client.email, client.full_name, "deposit",
                        f"{loan.amount} {disbursement_account.currency} (Loan Disbursement)",
                        disbursement_account.nickname or disbursement_account.type.value,
                        f"{disbursement_account.balance} {disbursement_account.currency}",
                    )
                except Exception:
                    pass

    elif approval.entity_type == ApprovalEntityType.card:
        card_result = await db.execute(select(Card).where(Card.id == approval.entity_id))
        card = card_result.scalar_one_or_none()
        if card:
            card.status = CardStatus.active

    approval.status = ApprovalStatus.approved
    approval.approved_by = current_user.id
    approval.notes = payload.notes

    await log_action(
        db, current_user.id, "approve", approval.entity_type.value, approval.entity_id,
        details={"approval_id": approval.id, "notes": payload.notes},
    )

    await db.commit()
    await db.refresh(approval)
    return approval


@router.post("/{approval_id}/reject", response_model=ApprovalOut, dependencies=[Depends(require_role(UserRole.employee, UserRole.admin))])
async def reject_request(
    approval_id: str,
    payload: ApprovalActionRequest,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(select(Approval).where(Approval.id == approval_id))
    approval = result.scalar_one_or_none()
    if not approval:
        raise HTTPException(status_code=404, detail="Approval not found")
    if approval.status != ApprovalStatus.pending:
        raise HTTPException(status_code=400, detail=f"Approval is already {approval.status.value}")

    if approval.entity_type == ApprovalEntityType.loan:
        loan_result = await db.execute(select(Loan).where(Loan.id == approval.entity_id))
        loan = loan_result.scalar_one_or_none()
        if loan:
            loan.status = LoanStatus.rejected

    elif approval.entity_type == ApprovalEntityType.card:
        card_result = await db.execute(select(Card).where(Card.id == approval.entity_id))
        card = card_result.scalar_one_or_none()
        if card:
            card.status = CardStatus.blocked

    approval.status = ApprovalStatus.rejected
    approval.approved_by = current_user.id
    approval.notes = payload.notes

    await log_action(
        db, current_user.id, "reject", approval.entity_type.value, approval.entity_id,
        details={"approval_id": approval.id, "notes": payload.notes},
    )

    await db.commit()
    await db.refresh(approval)
    return approval