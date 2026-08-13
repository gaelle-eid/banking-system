from decimal import Decimal
from datetime import datetime, timedelta

from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.models import Transaction, TransactionType, TransactionStatus

MAX_TRANSACTION_AMOUNT = Decimal("10000")
MAX_DAILY_TOTAL = Decimal("20000")
MIN_BALANCE_AFTER_WITHDRAWAL = Decimal("10")
NEW_FUNDING_SOURCE_DEPOSIT_CAP = Decimal("500")
NEW_FUNDING_SOURCE_WINDOW_HOURS = 24
MAX_CASH_BACK_PER_TRANSACTION = Decimal("100")

# ATM daily cash limits vary by card tier, matching how real banks tie
# withdrawal limits to account/card tier.
ATM_DAILY_LIMITS_BY_TIER = {
    "standard": Decimal("500"),
    "cashback": Decimal("1000"),
    "travel": Decimal("1000"),
    "premium": Decimal("2000"),
}


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

        remaining_balance = account.balance - amount
        # Allow withdrawing the FULL remaining balance (emptying the account,
        # e.g. to close it) as an exception to the minimum balance rule.
        if remaining_balance != 0 and remaining_balance < MIN_BALANCE_AFTER_WITHDRAWAL:
            raise ValueError(
                f"This would leave your account below the required minimum balance of {MIN_BALANCE_AFTER_WITHDRAWAL}. "
                f"Withdraw the full balance ({account.balance}) instead if you're trying to empty the account."
            )


def check_deposit_source_limit(funding_source, amount: Decimal):
    """Newly-verified funding sources are capped at a lower deposit amount
    for the first 24 hours, matching common real-world fraud prevention
    for freshly-linked accounts."""
    if not funding_source.verified_at:
        return  # shouldn't happen (deposits require verified sources), but don't crash if it does

    age = datetime.utcnow() - funding_source.verified_at
    if age < timedelta(hours=NEW_FUNDING_SOURCE_WINDOW_HOURS) and amount > NEW_FUNDING_SOURCE_DEPOSIT_CAP:
        raise ValueError(
            f"This funding source was linked recently, so deposits are capped at "
            f"{NEW_FUNDING_SOURCE_DEPOSIT_CAP} for the first {NEW_FUNDING_SOURCE_WINDOW_HOURS} hours. "
            f"This limit will lift automatically."
        )


async def check_atm_withdrawal_limit(db: AsyncSession, account_id: str, amount: Decimal, card_tier: str = "standard"):
    """ATM cash withdrawals have their own, lower daily cap - on top of the
    general daily movement limit - matching real-world ATM cash limits.
    The cap itself varies by card tier."""
    daily_cap = ATM_DAILY_LIMITS_BY_TIER.get(card_tier, ATM_DAILY_LIMITS_BY_TIER["standard"])
    start_of_day = datetime.utcnow().replace(hour=0, minute=0, second=0, microsecond=0)

    result = await db.execute(
        select(func.coalesce(func.sum(Transaction.amount), 0)).where(
            Transaction.account_id == account_id,
            Transaction.type == TransactionType.withdrawal,
            Transaction.method == "atm",
            Transaction.status == TransactionStatus.completed,
            Transaction.created_at >= start_of_day,
        )
    )
    todays_atm_total = Decimal(result.scalar() or 0)

    if todays_atm_total + amount > daily_cap:
        remaining = daily_cap - todays_atm_total
        raise ValueError(
            f"This would exceed your card's daily ATM withdrawal limit of {daily_cap}. "
            f"You have {max(remaining, Decimal(0))} remaining today. "
            f"For larger amounts, try a branch teller withdrawal instead."
        )