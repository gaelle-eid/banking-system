import json
from pydantic_ai import RunContext
from sqlalchemy import select
import re

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




async def _resolve_own_account(ctx: RunContext[ClientAgentDeps], account_type: str | None, account_nickname: str | None):
    """Shared helper: find one of the client's own accounts by nickname,
    or by the last 4 digits if the client used a masked-number label like
    'Checking ••••0001', or by type."""
    if account_nickname:
        result = await ctx.deps.db.execute(
            select(Account).where(Account.owner_id == ctx.deps.user_id)
        )
        all_accounts = result.scalars().all()

        # Try exact/partial nickname match first
        for acc in all_accounts:
            if acc.nickname and acc.nickname.lower() == account_nickname.strip().lower():
                return acc, None

        # Fall back: extract any 4-digit sequence from the input and match
        # against the account number's last 4 digits (handles labels like
        # "Checking ••••0001" which aren't real stored nicknames)
        digits = re.findall(r"\d{4}", account_nickname)
        if digits:
            last4 = digits[-1]
            for acc in all_accounts:
                if acc.account_number.endswith(last4):
                    return acc, None

        return None, f"I couldn't find an account matching '{account_nickname}'."

    if account_type:
        result = await ctx.deps.db.execute(
            select(Account).where(
                Account.owner_id == ctx.deps.user_id,
                Account.type == account_type.lower(),
            )
        )
        matches = result.scalars().all()
        if not matches:
            return None, f"You don't have a {account_type} account."
        if len(matches) > 1:
            options = ", ".join(f"{a.nickname} ({mask_account_number(a.account_number)})" for a in matches)
            return None, f"You have multiple {account_type} accounts: {options}. Which one do you mean?"
        return matches[0], None

    return None, "I need either an account nickname or type (checking/savings)."


async def propose_transfer(
    ctx: RunContext[ClientAgentDeps],
    amount: float,
    from_account_type: str | None = None,
    from_account_nickname: str | None = None,
    to_own_account_type: str | None = None,
    to_own_account_nickname: str | None = None,
    to_recipient_email: str | None = None,
    to_account_nickname: str | None = None,
) -> str:
    """Propose a transfer FROM one of the client's own accounts.

    For the SOURCE account (always the client's own), use from_account_type
    ('checking'/'savings') or from_account_nickname if they have multiple of
    the same type.

    For the DESTINATION, there are two cases:
    1. Moving money between the client's OWN accounts (e.g. "from checking
       to savings") - use to_own_account_type or to_own_account_nickname.
    2. Sending money to someone ELSE - use to_recipient_email to look up
       the recipient automatically, and to_account_nickname only if they
       have multiple accounts and you need to disambiguate (from the list
       you showed the client).

    NEVER ask for or mention a raw account number - use nicknames and
    masked numbers only. This does NOT execute the transfer immediately -
    it creates a pending action the client must confirm separately."""

    from_account, err = await _resolve_own_account(ctx, from_account_type, from_account_nickname)
    if err:
        return err

    if from_account.balance < amount:
        return f"Insufficient funds: {from_account.nickname} balance is {from_account.balance}, requested {amount}."

    to_account = None
    to_owner_name = "you"

    if to_own_account_type or to_own_account_nickname:
        to_account, err = await _resolve_own_account(ctx, to_own_account_type, to_own_account_nickname)
        if err:
            return err
        if to_account.id == from_account.id:
            return "The source and destination accounts can't be the same."

    elif to_recipient_email:
        result = await ctx.deps.db.execute(select(User).where(User.email == to_recipient_email))
        recipient = result.scalar_one_or_none()
        if not recipient:
            return "I couldn't find a client with that email."
        to_owner_name = recipient.full_name

        result = await ctx.deps.db.execute(select(Account).where(Account.owner_id == recipient.id))
        recipient_accounts = result.scalars().all()
        if not recipient_accounts:
            return f"{recipient.full_name} doesn't have any accounts yet."

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
    else:
        return "I need to know the destination: either one of your own accounts, or a recipient's email."

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
        f"({mask_account_number(from_account.account_number)}) to "
        f"{'your' if to_owner_name == 'you' else to_owner_name + chr(39) + 's'} {to_account.nickname} "
        f"({mask_account_number(to_account.account_number)}). "
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