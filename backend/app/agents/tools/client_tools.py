import json
from pydantic_ai import RunContext
from sqlalchemy import select

from app.agents.deps import ClientAgentDeps
from app.models.models import Account, Transaction, User, AgentActionLog, AgentActionStatus


def mask_account_number(account_number: str) -> str:
    return f"••••{account_number[-4:]}"


async def get_my_accounts(ctx: RunContext[ClientAgentDeps]) -> str:
    """Get a summary of the client's accounts and balances. ALWAYS refer to
    accounts by their nickname when talking to the client - never mention
    the internal id or full account number."""
    result = await ctx.deps.db.execute(
        select(Account).where(Account.owner_id == ctx.deps.user_id)
    )
    accounts = result.scalars().all()
    if not accounts:
        return "You have no accounts yet."

    lines = []
    for acc in accounts:
        display_name = acc.nickname or f"{acc.type.value.capitalize()} {mask_account_number(acc.account_number)}"
        lines.append(
            f"{display_name} ({acc.type.value}, {mask_account_number(acc.account_number)}): "
            f"{acc.balance} {acc.currency}"
        )
    return "\n".join(lines)

async def get_transaction_history(ctx: RunContext[ClientAgentDeps], account_nickname: str, limit: int = 10) -> str:
    """Get recent transaction history for one of the client's accounts,
    identified by its nickname (e.g. 'Emergency Fund', 'Checking 1')."""
    result = await ctx.deps.db.execute(
        select(Account).where(
            Account.owner_id == ctx.deps.user_id,
            Account.nickname.ilike(account_nickname),
        )
    )
    account = result.scalar_one_or_none()
    if not account:
        return "I couldn't find an account with that nickname. Ask me to list your accounts if you're not sure of the name."

    result = await ctx.deps.db.execute(
        select(Transaction)
        .where(Transaction.account_id == account.id)
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


async def propose_transfer(
    ctx: RunContext[ClientAgentDeps],
    from_account_type: str,
    amount: float,
    to_recipient_email: str | None = None,
    from_account_nickname: str | None = None,
    to_account_nickname: str | None = None,
) -> str:
    """Propose a transfer from one of the client's own accounts to a
    destination. Prefer from_account_type ('checking'/'savings') for the
    client's own account. If the client has multiple accounts of that type,
    or explicitly names a specific account, use from_account_nickname
    instead. The destination is normally the recipient's email address,
    looked up automatically. If the recipient has multiple accounts, use
    to_account_nickname (from the list you showed the client) to pick one.
    NEVER ask for or mention a raw account number - use nicknames and masked
    numbers only. This does NOT execute the transfer immediately - it
    creates a pending action the client must confirm separately."""

    if from_account_nickname:
        result = await ctx.deps.db.execute(
            select(Account).where(
                Account.owner_id == ctx.deps.user_id,
                Account.nickname.ilike(from_account_nickname),
            )
        )
        from_account = result.scalar_one_or_none()
        if not from_account:
            return "I couldn't find an account with that nickname."
    else:
        result = await ctx.deps.db.execute(
            select(Account).where(
                Account.owner_id == ctx.deps.user_id,
                Account.type == from_account_type.lower(),
            )
        )
        matching_accounts = result.scalars().all()

        if not matching_accounts:
            return f"You don't have a {from_account_type} account."
        if len(matching_accounts) > 1:
            options = ", ".join(
                f"{a.nickname} ({mask_account_number(a.account_number)})" for a in matching_accounts
            )
            return f"You have multiple {from_account_type} accounts: {options}. Which one should I use?"

        from_account = matching_accounts[0]

    if from_account.balance < amount:
        return f"Insufficient funds: {from_account.nickname} balance is {from_account.balance}, requested {amount}."

    if not to_recipient_email:
        return "I need the recipient's email to send money to them."

    result = await ctx.deps.db.execute(select(User).where(User.email == to_recipient_email))
    recipient = result.scalar_one_or_none()
    if not recipient:
        return "I couldn't find a client with that email."

    result = await ctx.deps.db.execute(select(Account).where(Account.owner_id == recipient.id))
    recipient_accounts = result.scalars().all()
    if not recipient_accounts:
        return f"{recipient.full_name} doesn't have any accounts yet."

    to_account = None
    if to_account_nickname:
        to_account = next(
            (a for a in recipient_accounts if a.nickname and a.nickname.lower() == to_account_nickname.lower()),
            None,
        )
        if not to_account:
            return f"I couldn't find an account named '{to_account_nickname}' for {recipient.full_name}."
    elif len(recipient_accounts) > 1:
        options = ", ".join(
            f"{a.nickname} ({a.type.value}, {mask_account_number(a.account_number)})" for a in recipient_accounts
        )
        return f"{recipient.full_name} has multiple accounts: {options}. Which one should receive the transfer?"
    else:
        to_account = recipient_accounts[0]

    action = AgentActionLog(
        conversation_id=ctx.deps.conversation_id,
        tool_name="transfer",
        input=json.dumps({
            "from_account_id": from_account.id,
            "to_account_id": to_account.id,
            "amount": str(amount),
        }),
        status=AgentActionStatus.pending_approval,
    )
    ctx.deps.db.add(action)
    await ctx.deps.db.flush()

    return (
        f"I've prepared a transfer of {amount} from your {from_account.nickname} "
        f"({mask_account_number(from_account.account_number)}) to {recipient.full_name}'s "
        f"{to_account.nickname} ({mask_account_number(to_account.account_number)}). "
        f"This hasn't been executed yet - please confirm it using action id {action.id}."
    )


async def find_recipient_account(ctx: RunContext[ClientAgentDeps], recipient_email: str) -> str:
    """Look up another client's account by their email address, so the
    current client doesn't need to know the recipient's account number."""
    result = await ctx.deps.db.execute(select(User).where(User.email == recipient_email))
    recipient = result.scalar_one_or_none()
    if not recipient:
        return "I couldn't find a client with that email."

    result = await ctx.deps.db.execute(select(Account).where(Account.owner_id == recipient.id))
    accounts = result.scalars().all()
    if not accounts:
        return f"{recipient.full_name} doesn't have any accounts yet."

    lines = [f"{recipient.full_name}'s accounts:"]
    for acc in accounts:
        lines.append(f"- {acc.nickname} ({acc.type.value}, {mask_account_number(acc.account_number)})")
    return "\n".join(lines)