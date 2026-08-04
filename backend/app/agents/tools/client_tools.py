from pydantic_ai import RunContext
from sqlalchemy import select

from app.agents.deps import ClientAgentDeps
from app.models.models import Account, Transaction


async def get_my_accounts(ctx: RunContext[ClientAgentDeps]) -> str:
    """Get a summary of the client's accounts and balances."""
    result = await ctx.deps.db.execute(
        select(Account).where(Account.owner_id == ctx.deps.user_id)
    )
    accounts = result.scalars().all()
    if not accounts:
        return "You have no accounts yet."

    lines = []
    for acc in accounts:
        lines.append(
            f"Account {acc.account_number} ({acc.type.value}): "
            f"{acc.balance} {acc.currency} [id: {acc.id}]"
        )
    return "\n".join(lines)


async def get_transaction_history(ctx: RunContext[ClientAgentDeps], account_id: str, limit: int = 10) -> str:
    """Get recent transaction history for one of the client's accounts."""
    result = await ctx.deps.db.execute(
        select(Account).where(Account.id == account_id, Account.owner_id == ctx.deps.user_id)
    )
    account = result.scalar_one_or_none()
    if not account:
        return "That account was not found, or does not belong to you."

    result = await ctx.deps.db.execute(
        select(Transaction)
        .where(Transaction.account_id == account_id)
        .order_by(Transaction.created_at.desc())
        .limit(limit)
    )
    txs = result.scalars().all()
    if not txs:
        return "No transactions found for this account."

    lines = []
    for tx in txs:
        lines.append(f"{tx.created_at.date()} | {tx.type.value} | {tx.amount} | {tx.status.value}")
    return "\n".join(lines)


async def explain_faq(ctx: RunContext[ClientAgentDeps], question: str) -> str:
    """Answer general banking FAQ questions (how transfers work, what a statement is, etc.)."""
    # Simple static FAQ for now; can be replaced with RAG later like SIS.
    faq = {
        "transfer": "Transfers move money between two accounts. They're recorded as two linked transactions: a debit from the sender and a credit to the receiver.",
        "statement": "A statement summarizes all transactions on an account over a period of time.",
        "loan": "Loan requests are reviewed by a bank employee before being approved and activated.",
        "card": "Card requests are reviewed by a bank employee before the card becomes active.",
    }
    q_lower = question.lower()
    for key, answer in faq.items():
        if key in q_lower:
            return answer
    return "I don't have a specific answer for that in my FAQ, but I can help you check your accounts, transactions, or submit a request."