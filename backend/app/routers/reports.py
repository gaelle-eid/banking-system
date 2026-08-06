from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func
from datetime import datetime

from app.core.database import get_db
from app.core.deps import require_role
from app.models.models import (
    Account, User, UserRole, Approval, ApprovalStatus,
    Transaction, Loan, LoanStatus, Card, CardStatus,
)
from app.schemas.report import BankSummaryReport

router = APIRouter(prefix="/reports", tags=["reports"])


@router.get("/summary", response_model=BankSummaryReport, dependencies=[Depends(require_role(UserRole.employee, UserRole.admin))])
async def bank_summary(db: AsyncSession = Depends(get_db)):
    total_accounts = (await db.execute(select(func.count(Account.id)))).scalar() or 0
    total_balance = (await db.execute(select(func.coalesce(func.sum(Account.balance), 0)))).scalar() or 0
    total_clients = (await db.execute(select(func.count(User.id)).where(User.role == UserRole.client))).scalar() or 0
    total_employees = (await db.execute(select(func.count(User.id)).where(User.role == UserRole.employee))).scalar() or 0
    pending_approvals = (await db.execute(select(func.count(Approval.id)).where(Approval.status == ApprovalStatus.pending))).scalar() or 0

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
        transactions_today=transactions_today,
        active_loans=active_loans,
        active_cards=active_cards,
    )