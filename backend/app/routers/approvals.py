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
    TransactionCategory, User, UserRole, RegistrationStatus, FraudFlag, FraudFlagStatus, FraudFlagSeverity,
)
from app.schemas.approval import ApprovalOut, ApprovalActionRequest

router = APIRouter(prefix="/approvals", tags=["approvals"])

# Loans at or above this amount require admin sign-off, not just any
# employee - a simple maker-checker control real banks use for large exposure.
LARGE_LOAN_THRESHOLD = Decimal("10000")


async def _build_client_context(db: AsyncSession, client_id: str) -> dict:
    """Relationship/risk snapshot for the client behind a request - real
    underwriters check this before evaluating the request in isolation."""
    client_result = await db.execute(select(User).where(User.id == client_id))
    client = client_result.scalar_one_or_none()

    accounts_result = await db.execute(select(Account).where(Account.owner_id == client_id))
    accounts = accounts_result.scalars().all()
    account_ids = [a.id for a in accounts]

    active_loans_result = await db.execute(
        select(Loan).where(Loan.client_id == client_id, Loan.status == LoanStatus.active)
    )
    active_loans = active_loans_result.scalars().all()

    active_cards_count = 0
    fraud_count = 0
    highest_severity = None
    if account_ids:
        cards_result = await db.execute(
            select(Card).where(Card.account_id.in_(account_ids), Card.status == CardStatus.active)
        )
        active_cards_count = len(cards_result.scalars().all())

        fraud_result = await db.execute(
            select(FraudFlag).where(FraudFlag.account_id.in_(account_ids), FraudFlag.status == FraudFlagStatus.pending)
        )
        fraud_flags = fraud_result.scalars().all()
        fraud_count = len(fraud_flags)
        if fraud_flags:
            severities = [f.severity.value for f in fraud_flags]
            for level in ("high", "medium", "low"):
                if level in severities:
                    highest_severity = level
                    break

    return {
        "member_since": client.created_at.isoformat() if client else None,
        "is_verified": client.is_verified if client else False,
        "registration_status": client.registration_status.value if client and client.registration_status else None,
        "account_count": len(accounts),
        "active_loans_count": len(active_loans),
        "active_loans_remaining": str(sum((l.remaining_balance or Decimal("0")) for l in active_loans)),
        "active_cards_count": active_cards_count,
        "pending_fraud_flags": fraud_count,
        "highest_fraud_severity": highest_severity,
    }


async def _build_credit_assessment(db: AsyncSession, client_id: str, requested_amount: Decimal, requested_term_months: int) -> dict:
    """Simulated credit assessment using real internal signals, since there's
    no external credit bureau to pull from - average income (actual deposit
    history) versus existing loan debt burden, the same underwriting logic
    a real bank applies, just without a third-party credit score."""
    accounts_result = await db.execute(select(Account).where(Account.owner_id == client_id))
    account_ids = [a.id for a in accounts_result.scalars().all()]

    ninety_days_ago = datetime.utcnow() - timedelta(days=90)
    avg_monthly_income = Decimal("0")
    if account_ids:
        income_result = await db.execute(
            select(Transaction).where(
                Transaction.account_id.in_(account_ids),
                Transaction.category == TransactionCategory.income,
                Transaction.created_at >= ninety_days_ago,
                Transaction.status == TransactionStatus.completed,
            )
        )
        income_txs = income_result.scalars().all()
        total_income = sum((t.amount for t in income_txs), Decimal("0"))
        avg_monthly_income = total_income / Decimal("3")

    other_loans_result = await db.execute(
        select(Loan).where(Loan.client_id == client_id, Loan.status == LoanStatus.active)
    )
    other_loans = other_loans_result.scalars().all()
    existing_monthly_debt = sum((l.monthly_payment or Decimal("0")) for l in other_loans)

    if avg_monthly_income > 0:
        debt_to_income_pct = float((existing_monthly_debt / avg_monthly_income) * 100)
        if debt_to_income_pct < 20:
            risk_tier = "Low"
        elif debt_to_income_pct < 40:
            risk_tier = "Medium"
        else:
            risk_tier = "High"
    else:
        debt_to_income_pct = None
        risk_tier = "Insufficient income history"

    return {
        "avg_monthly_income": str(avg_monthly_income),
        "existing_monthly_debt": str(existing_monthly_debt),
        "debt_to_income_pct": round(debt_to_income_pct, 1) if debt_to_income_pct is not None else None,
        "risk_tier": risk_tier,
    }


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
    approvals = result.scalars().all()

    enriched = []
    for approval in approvals:
        requester_result = await db.execute(select(User).where(User.id == approval.requested_by))
        requester = requester_result.scalar_one_or_none()
        requested_by_name = requester.full_name if requester else None

        details = None
        if approval.entity_type == ApprovalEntityType.loan:
            loan_result = await db.execute(select(Loan).where(Loan.id == approval.entity_id))
            loan = loan_result.scalar_one_or_none()
            if loan:
                account_result = await db.execute(select(Account).where(Account.id == loan.disbursement_account_id))
                account = account_result.scalar_one_or_none()
                account_label = None
                if account:
                    masked = f"••••{account.account_number[-4:]}"
                    account_label = f"{account.nickname or account.type.value} {masked}"
                credit_assessment = await _build_credit_assessment(db, loan.client_id, loan.amount, int(loan.term_months))
                details = {
                    "amount": str(loan.amount),
                    "term_months": int(loan.term_months),
                    "purpose": loan.purpose,
                    "disbursement_account": account_label,
                    "currency": account.currency if account else "USD",
                    "credit_assessment": credit_assessment,
                }
        elif approval.entity_type == ApprovalEntityType.card:
            card_result = await db.execute(select(Card).where(Card.id == approval.entity_id))
            card = card_result.scalar_one_or_none()
            if card:
                account_result = await db.execute(select(Account).where(Account.id == card.account_id))
                account = account_result.scalar_one_or_none()
                account_label = None
                if account:
                    masked = f"••••{account.account_number[-4:]}"
                    account_label = f"{account.nickname or account.type.value} {masked}"
                details = {
                    "type": card.type.value,
                    "tier": card.tier.value,
                    "account": account_label,
                }

        client_context = await _build_client_context(db, approval.requested_by)

        requires_admin = False
        if approval.entity_type == ApprovalEntityType.loan and details:
            requires_admin = Decimal(details["amount"]) >= LARGE_LOAN_THRESHOLD

        approval_out = ApprovalOut.model_validate(approval)
        approval_out.requested_by_name = requested_by_name
        approval_out.requested_by_email = requester.email if requester else None
        approval_out.details = details
        approval_out.client_context = client_context
        approval_out.requires_admin = requires_admin
        enriched.append(approval_out)

    return enriched


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
            if loan.amount >= LARGE_LOAN_THRESHOLD and current_user.role != UserRole.admin:
                raise HTTPException(
                    status_code=403,
                    detail=f"Loans of {LARGE_LOAN_THRESHOLD} or more require admin sign-off, not just an employee.",
                )
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