import json
from decimal import Decimal
from pydantic_ai import RunContext
from sqlalchemy import select
import re
from app.agents.deps import ClientAgentDeps
from app.core.account_access import get_accessible_accounts, get_accessible_account_ids
from app.models.models import Account, Transaction, User, AgentActionLog, AgentActionStatus


def mask_account_number(account_number: str) -> str:
    return f"••••{account_number[-4:]}"


async def get_my_accounts(ctx: RunContext[ClientAgentDeps]) -> str:
    """Get a summary of the client's accounts and balances. ALWAYS refer to
    accounts by their nickname when talking to the client - never mention
    the internal id or full account number."""
    accounts = await get_accessible_accounts(ctx.deps.db, ctx.deps.user_id)
    if not accounts:
        return "You have no accounts yet."

    lines = []
    for acc in accounts:
        display_name = acc.nickname or f"{acc.type.value.capitalize()} {mask_account_number(acc.account_number)}"
        joint_note = " [joint account]" if acc.owner_id != ctx.deps.user_id else ""
        lines.append(
            f"{display_name}{joint_note} ({acc.type.value}, {mask_account_number(acc.account_number)}): "
            f"{acc.balance} {acc.currency}"
        )
    return "\n".join(lines)


async def get_balance_in_currency(
    ctx: RunContext[ClientAgentDeps],
    target_currency: str,
    account_nickname: str | None = None,
    account_type: str | None = None,
) -> str:
    """Show what one of the client's account balances is worth in a
    different currency (e.g. 'what's my checking balance in EUR?').
    target_currency should be a 3-letter code like USD, EUR, GBP, LBP, JOD.
    If account_nickname/account_type aren't given and the client has only
    one account, that one is used automatically."""
    from app.core.exchange_rates import convert as convert_currency

    if account_nickname or account_type:
        account, err = await _resolve_own_account(ctx, account_type, account_nickname)
        if err:
            return err
    else:
        accounts = await get_accessible_accounts(ctx.deps.db, ctx.deps.user_id)
        if not accounts:
            return "You don't have any accounts yet."
        if len(accounts) > 1:
            options = ", ".join(a.nickname or a.type.value for a in accounts)
            return f"You have multiple accounts: {options}. Which one do you mean?"
        account = accounts[0]

    try:
        converted, rate = await convert_currency(account.balance, account.currency, target_currency.upper())
    except ValueError:
        return f"I don't have exchange rate data for {target_currency.upper()}. Supported currencies: USD, EUR, GBP, LBP, JOD."
    except Exception:
        return "The exchange rate service is temporarily unavailable - please try again in a moment."

    return (
        f"Your {account.nickname} balance of {account.balance} {account.currency} is "
        f"approximately {converted} {target_currency.upper()} (rate: 1 {account.currency} = {rate} {target_currency.upper()})."
    )


async def get_transaction_history(ctx: RunContext[ClientAgentDeps], account_nickname: str, limit: int = 10) -> str:
    """Get recent transaction history for one of the client's accounts,
    identified by its nickname (e.g. 'Emergency Fund', 'Checking 1')."""
    accessible_accounts = await get_accessible_accounts(ctx.deps.db, ctx.deps.user_id)
    account = next(
        (a for a in accessible_accounts if a.nickname and a.nickname.lower() == account_nickname.strip().lower()),
        None,
    )
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
        all_accounts = await get_accessible_accounts(ctx.deps.db, ctx.deps.user_id)

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
        all_accounts = await get_accessible_accounts(ctx.deps.db, ctx.deps.user_id)
        matches = [a for a in all_accounts if a.type.value == account_type.lower()]
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

    conversion_note = ""
    if from_account.currency != to_account.currency:
        try:
            from app.core.exchange_rates import convert as convert_currency
            converted, rate = await convert_currency(Decimal(str(amount)), from_account.currency, to_account.currency)
            conversion_note = (
                f" This will be converted at today's rate (1 {from_account.currency} = {rate} "
                f"{to_account.currency}), crediting approximately {converted} {to_account.currency}."
            )
        except Exception:
            conversion_note = f" Note: this converts from {from_account.currency} to {to_account.currency} at the live rate when confirmed."

    return (
        f"I've prepared a transfer of {amount} {from_account.currency} from your {from_account.nickname} "
        f"({mask_account_number(from_account.account_number)}) to "
        f"{'your' if to_owner_name == 'you' else to_owner_name + chr(39) + 's'} {to_account.nickname} "
        f"({mask_account_number(to_account.account_number)}).{conversion_note} "
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


async def get_recent_recipients(ctx: RunContext[ClientAgentDeps]) -> str:
    """Get a list of people the client has sent money to before, so they
    can be referred to by name instead of needing their email again."""
    my_account_ids = await get_accessible_account_ids(ctx.deps.db, ctx.deps.user_id)
    if not my_account_ids:
        return "You haven't sent any transfers yet."

    from app.models.models import TransactionType

    debit_result = await ctx.deps.db.execute(
        select(Transaction)
        .where(
            Transaction.account_id.in_(my_account_ids),
            Transaction.type == TransactionType.transfer_debit,
            Transaction.transfer_group_id.isnot(None),
        )
        .order_by(Transaction.created_at.desc())
    )
    my_debits = debit_result.scalars().all()

    seen = {}
    for debit in my_debits:
        credit_result = await ctx.deps.db.execute(
            select(Transaction).where(
                Transaction.transfer_group_id == debit.transfer_group_id,
                Transaction.type == TransactionType.transfer_credit,
            )
        )
        credit = credit_result.scalar_one_or_none()
        if not credit:
            continue
        acc_result = await ctx.deps.db.execute(select(Account).where(Account.id == credit.account_id))
        recipient_account = acc_result.scalar_one_or_none()
        if not recipient_account or recipient_account.id in my_account_ids:
            continue
        user_result = await ctx.deps.db.execute(select(User).where(User.id == recipient_account.owner_id))
        recipient_user = user_result.scalar_one_or_none()
        if recipient_user and recipient_user.id not in seen:
            seen[recipient_user.id] = f"{recipient_user.full_name} ({recipient_user.email})"

    if not seen:
        return "You haven't sent money to anyone else yet."
    return "People you've sent money to before:\n" + "\n".join(seen.values())


async def recommend_card_tier(ctx: RunContext[ClientAgentDeps]) -> str:
    """Analyze the client's transaction history and recommend a card tier
    (standard, cashback, travel, or premium) with reasoning based on their
    spending patterns and account balances."""
    accounts = await get_accessible_accounts(ctx.deps.db, ctx.deps.user_id)
    if not accounts:
        return "You need at least one account before I can recommend a card."

    total_balance = sum(float(a.balance) for a in accounts)
    account_ids = [a.id for a in accounts]

    tx_result = await ctx.deps.db.execute(
        select(Transaction).where(Transaction.account_id.in_(account_ids))
    )
    txs = tx_result.scalars().all()

    total_outgoing = sum(float(t.amount) for t in txs if t.type.value in ("withdrawal", "transfer_debit"))
    transfer_count = sum(1 for t in txs if t.type.value in ("transfer_debit", "transfer_credit"))
    tx_count = len(txs)

    # Simple, explainable heuristic (no real merchant-category data available yet)
    if total_balance >= 5000 and total_outgoing >= 2000:
        tier = "premium"
        reason = (
            f"You maintain a strong balance (~${total_balance:.0f}) and move significant money "
            f"(~${total_outgoing:.0f} in withdrawals/transfers). A Premium card offers the highest "
            f"limits and best perks for that level of activity."
        )
    elif transfer_count >= 5:
        tier = "travel"
        reason = (
            f"You've made {transfer_count} transfers, suggesting frequent movement of money "
            f"(possibly across accounts or to others). A Travel card rewards this kind of "
            f"active, flexible spending with travel-related perks."
        )
    elif tx_count >= 5:
        tier = "cashback"
        reason = (
            f"You have {tx_count} transactions on record - regular, everyday activity. "
            f"A Cashback card rewards frequent spending with a percentage back on every purchase."
        )
    else:
        tier = "standard"
        reason = (
            "You don't have much transaction history yet. A Standard card is a solid starting "
            "point with no annual fee - I can suggest an upgrade once I see more activity."
        )

    return (
        f"Based on your activity, I'd recommend a **{tier.capitalize()} card**.\n\n{reason}\n\n"
        f"Want me to prepare a card request for you at this tier?"
    )


async def propose_phone_transfer(
    ctx: RunContext[ClientAgentDeps],
    amount: float,
    to_phone: str,
    from_account_type: str | None = None,
    from_account_nickname: str | None = None,
) -> str:
    """Propose a transfer to someone by their PHONE NUMBER instead of email.
    This requires OTP verification for extra security - a code will be sent
    to the client's email (simulating SMS), which they must provide before
    the transfer executes. Use this when the client explicitly wants to
    send by phone number rather than email."""

    from_account, err = await _resolve_own_account(ctx, from_account_type, from_account_nickname)
    if err:
        return err

    if from_account.balance < amount:
        return f"Insufficient funds: {from_account.nickname} balance is {from_account.balance}, requested {amount}."

    result = await ctx.deps.db.execute(select(User).where(User.phone == to_phone))
    recipient = result.scalar_one_or_none()
    if not recipient:
        return "I couldn't find a client with that phone number."
    if not recipient.phone_verified:
        return f"{recipient.full_name}'s phone number isn't verified, so I can't send to it."

    result = await ctx.deps.db.execute(select(Account).where(Account.owner_id == recipient.id).limit(1))
    to_account = result.scalar_one_or_none()
    if not to_account:
        return f"{recipient.full_name} doesn't have an account to receive the transfer."

    import random
    from datetime import datetime, timedelta
    from app.models.models import TransferVerification
    from app.core.email import send_transfer_otp_email
    from app.core.limits import is_new_phone_recipient, check_new_recipient_transfer_limit

    is_new = await is_new_phone_recipient(ctx.deps.db, ctx.deps.user_id, to_account.id)
    try:
        check_new_recipient_transfer_limit(is_new, Decimal(str(amount)))
    except ValueError as e:
        return str(e)

    otp = f"{random.randint(0, 999999):06d}"
    verification = TransferVerification(
        initiated_by=ctx.deps.user_id,
        from_account_id=from_account.id,
        to_account_id=to_account.id,
        amount=amount,
        otp=otp,
        otp_expires_at=datetime.utcnow() + timedelta(minutes=5),
    )
    ctx.deps.db.add(verification)
    await ctx.deps.db.flush()

    result = await ctx.deps.db.execute(select(User).where(User.id == ctx.deps.user_id))
    current_user = result.scalar_one()
    try:
        send_transfer_otp_email(current_user.email, current_user.full_name, otp, f"{amount} {from_account.currency}", recipient.full_name)
    except Exception:
        pass

    return (
        f"I've prepared a transfer of {amount} from your {from_account.nickname} to {recipient.full_name} "
        f"(via phone). For security, this needs a verification code - I've sent one to your email. "
        f"Reply with the 6-digit code to complete the transfer. Verification id: {verification.id}"
    )

async def confirm_phone_transfer_otp(
    ctx: RunContext[ClientAgentDeps],
    verification_id: str,
    otp: str,
) -> str:
    """Confirm a phone-based transfer using the OTP code the client
    received. This actually executes the transfer if the code is correct."""
    from datetime import datetime
    from app.models.models import TransferVerification, Transaction, TransactionType, TransactionStatus
    import uuid as uuid_module

    result = await ctx.deps.db.execute(select(TransferVerification).where(TransferVerification.id == verification_id))
    verification = result.scalar_one_or_none()
    if not verification:
        return "I couldn't find that transfer request."
    if verification.initiated_by != ctx.deps.user_id:
        return "This isn't your transfer to confirm."
    if verification.verified:
        return "This transfer was already completed."
    if verification.locked:
        return "Too many incorrect attempts were made on this transfer. Please start a new one."
    if datetime.utcnow() > verification.otp_expires_at:
        return "That code has expired. Please start the transfer again."
    if otp != verification.otp:
        from app.core.limits import MAX_OTP_ATTEMPTS
        verification.attempts = int(verification.attempts) + 1
        if int(verification.attempts) >= MAX_OTP_ATTEMPTS:
            verification.locked = True
            await ctx.deps.db.flush()
            return "That code doesn't match, and you've hit the maximum attempts - this transfer has been cancelled. Please start again."
        await ctx.deps.db.flush()
        remaining = MAX_OTP_ATTEMPTS - int(verification.attempts)
        return f"That code doesn't match. You have {remaining} attempt{'s' if remaining != 1 else ''} left."

    from_result = await ctx.deps.db.execute(select(Account).where(Account.id == verification.from_account_id))
    from_account = from_result.scalar_one_or_none()
    to_result = await ctx.deps.db.execute(select(Account).where(Account.id == verification.to_account_id))
    to_account = to_result.scalar_one_or_none()

    if not from_account or not to_account:
        return "One of the accounts no longer exists."
    if from_account.balance < verification.amount:
        return "Insufficient funds to complete this transfer now."

    from app.core.exchange_rates import convert as convert_currency

    exchange_rate = None
    credit_amount = verification.amount
    if from_account.currency != to_account.currency:
        try:
            credit_amount, exchange_rate = await convert_currency(
                verification.amount, from_account.currency, to_account.currency
            )
        except Exception:
            return "The exchange rate service is temporarily unavailable - please try confirming again in a moment."

    group_id = str(uuid_module.uuid4())
    from_account.balance -= verification.amount
    to_account.balance += credit_amount

    ctx.deps.db.add(Transaction(
        account_id=from_account.id, type=TransactionType.transfer_debit,
        amount=verification.amount, transfer_group_id=group_id,
        status=TransactionStatus.completed, initiated_by=ctx.deps.user_id,
        exchange_rate=exchange_rate,
    ))
    ctx.deps.db.add(Transaction(
        account_id=to_account.id, type=TransactionType.transfer_credit,
        amount=credit_amount, transfer_group_id=group_id,
        status=TransactionStatus.completed, initiated_by=ctx.deps.user_id,
        exchange_rate=exchange_rate,
    ))
    verification.verified = True
    await ctx.deps.db.flush()

    if exchange_rate:
        return f"Transfer completed successfully - {verification.amount} {from_account.currency} converted to {credit_amount} {to_account.currency}."
    return f"Transfer of {verification.amount} completed successfully."
async def analyze_spending(ctx: RunContext[ClientAgentDeps], account_nickname: str | None = None) -> str:
    """Analyze the client's recent spending (withdrawals and outgoing
    transfers) and give concrete, actionable advice on where they could
    cut back to save money - e.g. 'reduce X by 10% to save $Y/month'.
    If account_nickname is given, analyze just that account; otherwise
    analyze across all their accounts."""

    if account_nickname:
        account, err = await _resolve_own_account(ctx, None, account_nickname)
        if err:
            return err
        account_ids = [account.id]
    else:
        accounts = await get_accessible_accounts(ctx.deps.db, ctx.deps.user_id)
        if not accounts:
            return "You don't have any accounts yet."
        account_ids = [a.id for a in accounts]

    from datetime import datetime, timedelta
    thirty_days_ago = datetime.utcnow() - timedelta(days=30)

    result = await ctx.deps.db.execute(
        select(Transaction).where(
            Transaction.account_id.in_(account_ids),
            Transaction.type.in_(["withdrawal", "transfer_debit"]),
            Transaction.created_at >= thirty_days_ago,
        )
    )
    outgoing_txs = result.scalars().all()

    if not outgoing_txs:
        return "You haven't had any outgoing transactions in the last 30 days - nothing to analyze yet."

    total_outgoing = sum(float(t.amount) for t in outgoing_txs)
    withdrawal_total = sum(float(t.amount) for t in outgoing_txs if t.type.value == "withdrawal")
    transfer_total = sum(float(t.amount) for t in outgoing_txs if t.type.value == "transfer_debit")
    tx_count = len(outgoing_txs)
    avg_tx = total_outgoing / tx_count if tx_count else 0

    potential_savings_10pct = total_outgoing * 0.10

    lines = [
        f"Spending analysis (last 30 days):",
        f"- Total outgoing: {total_outgoing:.2f} across {tx_count} transactions",
        f"- Withdrawals: {withdrawal_total:.2f}",
        f"- Outgoing transfers: {transfer_total:.2f}",
        f"- Average transaction size: {avg_tx:.2f}",
        "",
        f"If you reduced overall outgoing spending by just 10%, you'd save "
        f"approximately {potential_savings_10pct:.2f} per month.",
    ]

    if withdrawal_total > transfer_total:
        lines.append(
            "Most of your outgoing money is cash withdrawals - consider tracking what these "
            "are for, since cash spending is often the easiest place to trim."
        )
    elif tx_count > 10:
        lines.append(
            f"You have a high number of transactions ({tx_count}) - frequent small transfers "
            "can add up. Consolidating them might help you spend more intentionally."
        )

    return "\n".join(lines)



async def propose_savings_goal(
    ctx: RunContext[ClientAgentDeps],
    goal_name: str,
    target_amount: float,
    source_account_type: str | None = None,
    source_account_nickname: str | None = None,
) -> str:
    """Propose creating a new savings goal with a dedicated account
    (e.g. 'Car', 'Vacation', 'Emergency Fund'). This creates a pending
    action the client must confirm before the goal account is actually
    created. source_account_type/nickname identifies which of the
    client's accounts contributions would come from later (checking,
    typically)."""

    source_account, err = await _resolve_own_account(ctx, source_account_type, source_account_nickname)
    if err:
        return err

    action = AgentActionLog(
        conversation_id=ctx.deps.conversation_id,
        tool_name="create_savings_goal",
        input=json.dumps({
            "goal_name": goal_name,
            "target_amount": str(target_amount),
            "source_account_id": source_account.id,
        }),
        status=AgentActionStatus.pending_approval,
    )
    ctx.deps.db.add(action)
    await ctx.deps.db.flush()

    return (
        f"I've prepared a new savings goal called '{goal_name}' with a target of {target_amount}. "
        f"This will create a dedicated '{goal_name}' savings account, with contributions coming from "
        f"your {source_account.nickname}. This hasn't been created yet - please confirm using action id {action.id}."
    )



async def contribute_to_goal(
    ctx: RunContext[ClientAgentDeps],
    goal_name: str,
    amount: float,
) -> str:
    """Propose a one-time contribution to an existing savings goal
    (used for variable/manual monthly contributions, or any extra
    contribution the client wants to make). This does NOT execute
    immediately - the client must confirm."""
    from app.models.models import SavingsGoal

    result = await ctx.deps.db.execute(
        select(SavingsGoal).where(
            SavingsGoal.client_id == ctx.deps.user_id,
            SavingsGoal.name.ilike(goal_name),
            SavingsGoal.active == True,
        )
    )
    goal = result.scalar_one_or_none()
    if not goal:
        return f"I couldn't find an active goal named '{goal_name}'."

    source_result = await ctx.deps.db.execute(select(Account).where(Account.id == goal.source_account_id))
    source_account = source_result.scalar_one_or_none()
    if not source_account:
        return "This goal doesn't have a funding account set up."
    if source_account.balance < amount:
        return f"Insufficient funds: your {source_account.nickname} balance is {source_account.balance}, requested {amount}."

    action = AgentActionLog(
        conversation_id=ctx.deps.conversation_id,
        tool_name="goal_contribution",
        input=json.dumps({
            "goal_id": goal.id,
            "source_account_id": source_account.id,
            "goal_account_id": goal.goal_account_id,
            "amount": str(amount),
        }),
        status=AgentActionStatus.pending_approval,
    )
    ctx.deps.db.add(action)
    await ctx.deps.db.flush()

    return (
        f"I've prepared a {amount} contribution to your '{goal.name}' goal from your "
        f"{source_account.nickname}. This hasn't been executed yet - please confirm using action id {action.id}."
    )