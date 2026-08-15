from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func
from datetime import datetime
from decimal import Decimal

from app.core.database import get_db
from app.core.deps import require_role
from app.core.exchange_rates import convert as convert_currency
from app.models.models import (
    Account, User, UserRole, RegistrationStatus, Approval, ApprovalStatus,
    Transaction, Loan, LoanStatus, Card, CardStatus, FraudFlag, FraudFlagStatus, FraudFlagSeverity,
)
from app.schemas.report import BankSummaryReport

router = APIRouter(prefix="/reports", tags=["reports"])


@router.get("/summary", response_model=BankSummaryReport, dependencies=[Depends(require_role(UserRole.employee, UserRole.admin))])
async def bank_summary(db: AsyncSession = Depends(get_db)):
    total_accounts = (await db.execute(select(func.count(Account.id)))).scalar() or 0

    # Sum balances PER CURRENCY first, then convert each currency's total to
    # USD once - summing raw balances across currencies directly would be
    # meaningless (e.g. LBP amounts are in the thousands vs small USD/EUR figures).
    currency_totals_result = await db.execute(
        select(Account.currency, func.coalesce(func.sum(Account.balance), 0)).group_by(Account.currency)
    )
    total_balance = Decimal("0")
    for currency, subtotal in currency_totals_result.all():
        if currency == "USD":
            total_balance += subtotal
        else:
            try:
                converted, _ = await convert_currency(subtotal, currency, "USD")
                total_balance += converted
            except Exception:
                pass  # skip currencies the rate service can't convert right now

    total_clients = (await db.execute(select(func.count(User.id)).where(User.role == UserRole.client))).scalar() or 0
    total_employees = (await db.execute(select(func.count(User.id)).where(User.role == UserRole.employee))).scalar() or 0
    pending_approvals = (await db.execute(select(func.count(Approval.id)).where(Approval.status == ApprovalStatus.pending))).scalar() or 0
    pending_registrations = (await db.execute(
        select(func.count(User.id)).where(User.registration_status == RegistrationStatus.pending_review)
    )).scalar() or 0
    pending_fraud_flags = (await db.execute(
        select(func.count(FraudFlag.id)).where(FraudFlag.status == FraudFlagStatus.pending)
    )).scalar() or 0
    high_severity_fraud_count = (await db.execute(
        select(func.count(FraudFlag.id)).where(
            FraudFlag.status == FraudFlagStatus.pending, FraudFlag.severity == FraudFlagSeverity.high
        )
    )).scalar() or 0

    start_of_day = datetime.utcnow().replace(hour=0, minute=0, second=0, microsecond=0)
    transactions_today = (await db.execute(
        select(func.count(Transaction.id)).where(Transaction.created_at >= start_of_day)
    )).scalar() or 0

    active_loans = (await db.execute(select(func.count(Loan.id)).where(Loan.status == LoanStatus.active))).scalar() or 0
    active_cards = (await db.execute(select(func.count(Card.id)).where(Card.status == CardStatus.active))).scalar() or 0

    return BankSummaryReport(
        total_accounts=total_accounts,
        total_balance=total_balance,
        total_clients=total_clients,
        total_employees=total_employees,
        pending_approvals=pending_approvals,
        pending_registrations=pending_registrations,
        pending_fraud_flags=pending_fraud_flags,
        high_severity_fraud_count=high_severity_fraud_count,
        transactions_today=transactions_today,
        active_loans=active_loans,
        active_cards=active_cards,
    )