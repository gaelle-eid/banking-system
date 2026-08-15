from datetime import datetime, timedelta
from decimal import Decimal
from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.models import Transaction, TransactionStatus, TransactionType, FraudFlag, FraudFlagSeverity
from app.core.email import send_email


async def would_trigger_velocity_block(db: AsyncSession, account_id: str) -> bool:
    """Real-time check run BEFORE a withdrawal/transfer executes - unlike
    the other rules below, which only flag a transaction for review AFTER
    it's already gone through. Rapid-fire activity (5+ money-out moves in
    5 minutes) is a strong enough signal of a compromised account or bot
    that real banks block it outright rather than review it after the fact."""
    five_min_ago = datetime.utcnow() - timedelta(minutes=5)
    result = await db.execute(
        select(func.count(Transaction.id)).where(
            Transaction.account_id == account_id,
            Transaction.type.in_([TransactionType.withdrawal, TransactionType.transfer_debit]),
            Transaction.created_at >= five_min_ago,
            Transaction.status == TransactionStatus.completed,
        )
    )
    recent_count = result.scalar() or 0
    return recent_count >= 4  # this new one would make it the 5th

async def check_transaction_for_fraud(db: AsyncSession, account, transaction, current_user) -> FraudFlag | None:
    """Run simple anomaly rules against a just-completed transaction.
    Returns a FraudFlag if something looks unusual, otherwise None."""

    reasons = []
    severity = FraudFlagSeverity.low

    # Rule 1: transaction significantly larger than this account's typical size
    result = await db.execute(
        select(func.avg(Transaction.amount), func.count(Transaction.id)).where(
            Transaction.account_id == account.id,
            Transaction.id != transaction.id,
            Transaction.status == TransactionStatus.completed,
        )
    )
    avg_amount, tx_count = result.first()
    if avg_amount and tx_count and tx_count >= 3:
        avg_amount = float(avg_amount)
        if float(transaction.amount) > avg_amount * 5 and float(transaction.amount) > 100:
            reasons.append(
                f"This transaction ({transaction.amount}) is more than 5x this account's "
                f"typical transaction size (avg {avg_amount:.2f})."
            )
            severity = FraudFlagSeverity.medium

    # Rule 2: rapid repeated transactions in a short window
    five_min_ago = datetime.utcnow() - timedelta(minutes=5)
    result = await db.execute(
        select(func.count(Transaction.id)).where(
            Transaction.account_id == account.id,
            Transaction.id != transaction.id,
            Transaction.created_at >= five_min_ago,
            Transaction.status == TransactionStatus.completed,
        )
    )
    recent_count = result.scalar() or 0
    if recent_count >= 3:
        reasons.append(f"{recent_count + 1} transactions occurred on this account within 5 minutes.")
        severity = FraudFlagSeverity.high

    # Rule 3: very large absolute amount regardless of history
    if float(transaction.amount) >= 5000:
        reasons.append(f"Large transaction amount: {transaction.amount}.")
        if severity == FraudFlagSeverity.low:
            severity = FraudFlagSeverity.medium

    if not reasons:
        return None

    flag = FraudFlag(
        transaction_id=transaction.id,
        account_id=account.id,
        reason=" ".join(reasons),
        severity=severity,
    )
    db.add(flag)

    try:
        send_email(
            current_user.email, "Unusual activity detected on your account",
            f"<p>Hi {current_user.full_name},</p>"
            f"<p>We noticed unusual activity on your account: <strong>{transaction.type.value} "
            f"of {transaction.amount}</strong>.</p>"
            f"<p>If this was you, no action is needed. If you don't recognize this activity, "
            f"please contact support immediately.</p>",
        )
    except Exception:
        pass

    return flag