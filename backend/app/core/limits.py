from decimal import Decimal
from datetime import datetime, timedelta

from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.models import Transaction, TransactionType, TransactionStatus

MAX_TRANSACTION_AMOUNT = Decimal("10000")
MAX_DAILY_TOTAL = Decimal("20000")
MIN_BALANCE_AFTER_WITHDRAWAL = Decimal("10")


async def get_todays_moved_total(db: AsyncSession, account_id: str) -> Decimal:
    """Sum of withdrawal + transfer_debit amounts for this account today."""
    start_of_day = datetime.utcnow().replace(hour=0, minute=0, second=0, microsecond=0)

    result = await db.execute(
        select(func.coalesce(func.sum(Transaction.amount), 0)).where(
            Transaction.account_id == account_id,
            Transaction.type.in_([TransactionType.withdrawal, TransactionType.transfer_debit]),
            Transaction.status == TransactionStatus.completed,
            Transaction.created_at >= start_of_day,
        )
    )
    return Decimal(result.scalar() or 0)


async def check_transaction_limits(db: AsyncSession, account, amount: Decimal, is_outgoing: bool):
    """Raises ValueError with a user-facing message if any limit is violated."""
    if amount > MAX_TRANSACTION_AMOUNT:
        raise ValueError(f"Amount exceeds the maximum allowed per transaction ({MAX_TRANSACTION_AMOUNT}).")

    if is_outgoing:
        todays_total = await get_todays_moved_total(db, account.id)
        if todays_total + amount > MAX_DAILY_TOTAL:
            remaining = MAX_DAILY_TOTAL - todays_total
            raise ValueError(
                f"This would exceed your daily limit of {MAX_DAILY_TOTAL}. "
                f"You have {max(remaining, Decimal(0))} remaining today."
            )

        if account.balance - amount < MIN_BALANCE_AFTER_WITHDRAWAL:
            raise ValueError(
                f"This would leave your account below the required minimum balance of {MIN_BALANCE_AFTER_WITHDRAWAL}."
            )