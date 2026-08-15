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
    """Analyze the client's REAL spending by category (last 30 days) plus
    their balance, and recommend a card tier (standard, cashback, travel,
    or premium) with reasoning grounded in what they actually spend on -
    not just a transaction count. Explicitly compares the recommended
    tier's benefits against the next most relevant alternative, so the
    client understands what they'd gain versus what they'd be leaving on
    the table with a different tier."""
    from datetime import datetime, timedelta

    accounts = await get_accessible_accounts(ctx.deps.db, ctx.deps.user_id)
    if not accounts:
        return "You need at least one account before I can recommend a card."

    total_balance = sum(float(a.balance) for a in accounts)
    account_ids = [a.id for a in accounts]

    thirty_days_ago = datetime.utcnow() - timedelta(days=30)
    tx_result = await ctx.deps.db.execute(
        select(Transaction).where(
            Transaction.account_id.in_(account_ids),
            Transaction.created_at >= thirty_days_ago,
        )
    )
    txs = tx_result.scalars().all()

    outgoing_txs = [t for t in txs if t.type.value in ("withdrawal", "transfer_debit")]
    total_outgoing = sum(float(t.amount) for t in outgoing_txs)
    tx_count = len(txs)

    category_totals = {}
    for t in outgoing_txs:
        if t.category:
            cat = t.category.value
            category_totals[cat] = category_totals.get(cat, 0.0) + float(t.amount)

    top_cat, top_amt = (None, 0.0)
    if category_totals:
        top_cat, top_amt = max(category_totals.items(), key=lambda c: c[1])
    top_label = top_cat.replace("_", " ").title() if top_cat else None
    top_pct = (top_amt / total_outgoing * 100) if total_outgoing else 0

    category_summary = ""
    if category_totals:
        sorted_cats = sorted(category_totals.items(), key=lambda c: c[1], reverse=True)[:3]
        category_summary = "Your top spending (last 30 days): " + ", ".join(
            f"{c.replace('_', ' ').title()} ({a:.2f})" for c, a in sorted_cats
        ) + ". "

    # Compact benefit summaries per tier, used to build an explicit
    # this-tier-vs-that-tier comparison rather than describing the
    # recommended tier in isolation.
    TIER_BENEFITS = {
        "standard": "no annual fee, but no rewards and no extra perks",
        "cashback": "2% cashback on every purchase, no annual fee, but nothing travel-specific",
        "travel": "no foreign transaction fees, 3x points on travel, free hotel breakfast, airport lounge access, travel insurance ($95/year)",
        "premium": "5% cashback plus full travel perks - free breakfast AND dinner, unlimited lounge access, 24/7 concierge ($250/year)",
    }

    if total_balance >= 5000 and total_outgoing >= 2000:
        tier, alt = "premium", "travel"
        reason = (
            f"{category_summary}You maintain a strong balance (~${total_balance:.0f}) and spend "
            f"significantly (~${total_outgoing:.0f}/month)."
        )
    elif top_cat == "travel":
        tier, alt = "travel", "cashback"
        reason = f"{category_summary}Travel is your biggest category at {top_pct:.0f}% of spending."
    elif top_cat in ("dining", "shopping", "entertainment"):
        tier, alt = "cashback", "travel"
        reason = f"{category_summary}{top_label} is your biggest category at {top_pct:.0f}% of spending."
    elif tx_count >= 5:
        tier, alt = "cashback", "standard"
        reason = f"{category_summary}You have {tx_count} transactions in the last 30 days - regular, everyday activity."
    else:
        tier, alt = "standard", "cashback"
        reason = "You don't have much recent transaction history yet."

    comparison = (
        f"With **{tier.capitalize()}**, you get: {TIER_BENEFITS[tier]}. "
        f"Compare that to **{alt.capitalize()}**, which gives you: {TIER_BENEFITS[alt]}. "
        f"Given your spending, {tier.capitalize()} puts more real value in your pocket than {alt.capitalize()} would."
    )

    return (
        f"Based on your real spending, I'd recommend a **{tier.capitalize()} card**.\n\n{reason}\n\n"
        f"{comparison}\n\n"
        f"Want me to prepare a card request for you at this tier?"
    )


async def propose_card_request(
    ctx: RunContext[ClientAgentDeps],
    account_type: str | None = None,
    account_nickname: str | None = None,
    card_type: str = "debit",
    tier: str = "standard",
) -> str:
    """Propose requesting a new card (debit or credit) at a given tier for
    one of the client's accounts. Only call this after the client has
    explicitly agreed to a specific tier - either one you recommended via
    recommend_card_tier, or one they named themselves. card_type must be
    'debit' or 'credit'; tier must be 'standard', 'cashback', 'travel', or
    'premium'. This creates a pending action the client must confirm -
    it does NOT create the card immediately. Requested cards still need
    employee approval before they're active, same as requesting one
    through the app directly."""
    from app.models.models import Card, CardType, CardStatus

    account, err = await _resolve_own_account(ctx, account_type, account_nickname)
    if err:
        return err

    if card_type not in ("debit", "credit"):
        return "Card type should be 'debit' or 'credit'."
    if tier not in ("standard", "cashback", "travel", "premium"):
        return "Tier should be one of: standard, cashback, travel, premium."

    if card_type == "debit":
        existing_result = await ctx.deps.db.execute(
            select(Card).where(
                Card.account_id == account.id,
                Card.type == CardType.debit,
                Card.status.in_([CardStatus.pending, CardStatus.active]),
            )
        )
        if existing_result.scalar_one_or_none():
            return f"{account.nickname} already has a debit card (active or pending) - only one is allowed per account."

    action = AgentActionLog(
        conversation_id=ctx.deps.conversation_id,
        tool_name="card_request",
        input=json.dumps({
            "account_id": account.id,
            "card_type": card_type,
            "tier": tier,
        }),
        status=AgentActionStatus.pending_approval,
    )
    ctx.deps.db.add(action)
    await ctx.deps.db.flush()

    return (
        f"I've prepared a {tier} {card_type} card request for {account.nickname}. Like all card "
        f"requests, it'll need employee approval before it's active - same as requesting one "
        f"directly in the app. This hasn't been submitted yet - please confirm using action id {action.id}."
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

    from app.models.models import TransactionCategory

    ctx.deps.db.add(Transaction(
        account_id=from_account.id, type=TransactionType.transfer_debit,
        amount=verification.amount, transfer_group_id=group_id,
        status=TransactionStatus.completed, initiated_by=ctx.deps.user_id,
        exchange_rate=exchange_rate, category=TransactionCategory.transfer_to_person,
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
    """Analyze the client's recent spending broken down by REAL category
    (dining, groceries, travel, shopping, etc. - based on what they've
    actually tagged their withdrawals and transfers as) and give concrete,
    specific advice - e.g. 'you spend $200/month on dining; cutting to
    $100 would save $100/month'. Use this whenever the client asks about
    their spending, wants budgeting advice, or is discussing a savings
    goal (always check this BEFORE proposing a goal timeline, so the
    numbers you give are grounded in their real habits, not guesses).
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
    tx_count = len(outgoing_txs)

    # Real category breakdown - only counts transactions that actually have
    # a spending category tag (uncategorized system moves are excluded).
    category_totals = {}
    uncategorized_total = 0.0
    for tx in outgoing_txs:
        if tx.category:
            cat = tx.category.value
            category_totals[cat] = category_totals.get(cat, 0.0) + float(tx.amount)
        else:
            uncategorized_total += float(tx.amount)

    sorted_categories = sorted(category_totals.items(), key=lambda c: c[1], reverse=True)

    lines = [
        f"Spending analysis (last 30 days): {total_outgoing:.2f} total across {tx_count} transactions.",
        "",
    ]

    if sorted_categories:
        lines.append("By category:")
        for cat, amt in sorted_categories:
            label = cat.replace("_", " ").title()
            pct = (amt / total_outgoing) * 100 if total_outgoing else 0
            lines.append(f"- {label}: {amt:.2f} ({pct:.0f}%)")
        if uncategorized_total:
            lines.append(f"- Uncategorized: {uncategorized_total:.2f}")
        lines.append("")

        top_category, top_amount = sorted_categories[0]
        top_label = top_category.replace("_", " ").title()
        cut_20pct = top_amount * 0.20
        cut_50pct = top_amount * 0.50
        lines.append(
            f"Your biggest category is {top_label} at {top_amount:.2f}/month. Some concrete options: "
            f"cutting it by 20% (to {top_amount - cut_20pct:.2f}) would free up {cut_20pct:.2f}/month, "
            f"or cutting it by half (to {top_amount - cut_50pct:.2f}) would free up {cut_50pct:.2f}/month. "
            f"Use these real numbers when discussing savings goals or timelines with the client - don't "
            f"just suggest a generic percentage of total spending."
        )
    else:
        lines.append(
            "None of these transactions have a spending category tag yet, so I can't break this down "
            "by what it was actually for - only a generic total is available."
        )

    return "\n".join(lines)


async def propose_savings_goal(
    ctx: RunContext[ClientAgentDeps],
    goal_name: str,
    target_amount: float,
    source_account_type: str | None = None,
    source_account_nickname: str | None = None,
    confirmed: bool = False,
) -> str:
    """Set up a new savings goal - this is a TWO-CALL tool, not two
    separate tools, so the study can never be skipped by accident.

    FIRST call (confirmed left as False, the default): call this as soon
    as the client has given you a goal name, target amount, and funding
    account. It returns a feasibility study - pros, cons, and a
    feasibility rating grounded in their real balance and spending.
    Present that study to the client EXACTLY as returned (it's already
    formatted) and then STOP. Do not say anything else and do not call
    this tool again in the same turn.

    SECOND call (confirmed=True): only call this again, with confirmed
    explicitly set to True, after the client's NEXT message clearly says
    yes/go ahead/let's do it. This actually creates the pending goal
    action, which the client must then confirm via the UI button.

    NEVER set confirmed=True on the first call, and never invent a goal
    name, amount, or account the client hasn't actually given you."""
    from datetime import datetime, timedelta

    source_account, err = await _resolve_own_account(ctx, source_account_type, source_account_nickname)
    if err:
        return err

    if not confirmed:
        # Step one: feasibility study only. No pending action is created here.
        thirty_days_ago = datetime.utcnow() - timedelta(days=30)
        accessible = await get_accessible_accounts(ctx.deps.db, ctx.deps.user_id)
        account_ids = [a.id for a in accessible]

        tx_result = await ctx.deps.db.execute(
            select(Transaction).where(
                Transaction.account_id.in_(account_ids),
                Transaction.type.in_(["withdrawal", "transfer_debit"]),
                Transaction.created_at >= thirty_days_ago,
                Transaction.category.isnot(None),
            )
        )
        recent_spending = tx_result.scalars().all()
        category_totals = {}
        for tx in recent_spending:
            cat = tx.category.value
            category_totals[cat] = category_totals.get(cat, 0.0) + float(tx.amount)

        balance = float(source_account.balance)
        pct_covered = min(100.0, (balance / target_amount) * 100) if target_amount else 0

        monthly_3mo = target_amount / 3
        monthly_6mo = target_amount / 6
        monthly_12mo = target_amount / 12

        # Realistic cut percentages by category type - discretionary
        # spending (dining, shopping, entertainment) can reasonably be
        # trimmed more than necessities (groceries, bills, healthcare),
        # unlike a flat "cut everything in half" assumption.
        CATEGORY_FLEXIBILITY = {
            "dining": 0.25,
            "entertainment": 0.25,
            "shopping": 0.25,
            "travel": 0.20,
            "cash_withdrawal": 0.15,
            "other": 0.15,
            "transfer_to_person": 0.10,
            "groceries": 0.10,
            "bills_utilities": 0.05,
            "healthcare": 0.05,
        }
        NECESSITY_CATEGORIES = {"groceries", "bills_utilities", "healthcare"}

        sorted_categories = sorted(category_totals.items(), key=lambda c: c[1], reverse=True)
        category_savings = []
        for cat, amt in sorted_categories:
            flex_pct = CATEGORY_FLEXIBILITY.get(cat, 0.15)
            savings = amt * flex_pct
            category_savings.append((cat, amt, flex_pct, savings))

        total_potential_savings = sum(s[3] for s in category_savings)

        if total_potential_savings >= monthly_6mo * 1.5:
            feasibility = "Comfortable"
        elif total_potential_savings >= monthly_6mo:
            feasibility = "Tight but doable"
        else:
            feasibility = "Ambitious"

        pros = []
        cons = []

        if balance > 0:
            pros.append(f"{source_account.nickname} already holds {balance:.2f}, covering {pct_covered:.0f}% of the target immediately.")
        else:
            cons.append(f"{source_account.nickname} currently has no balance - the full {target_amount:.2f} would need to come from future contributions.")

        # Show up to the top 3 categories with realistic, category-specific
        # cut suggestions, not just one category cut in half.
        if category_savings:
            for cat, amt, flex_pct, savings in category_savings[:3]:
                label = cat.replace("_", " ").title()
                kind = "a necessity - only modest cuts are realistic" if cat in NECESSITY_CATEGORIES else "discretionary - more flexible to cut"
                pros.append(
                    f"{label} ({amt:.2f}/month, {kind}): trimming {flex_pct*100:.0f}% would free up {savings:.2f}/month."
                )
            if len(category_savings) > 1:
                pros.append(f"Combined across these categories, a realistic monthly savings potential is about {total_potential_savings:.2f}.")
            necessity_share = sum(amt for cat, amt, _, _ in category_savings if cat in NECESSITY_CATEGORIES)
            total_spend = sum(amt for _, amt, _, _ in category_savings)
            if total_spend and necessity_share / total_spend > 0.5:
                cons.append("More than half of your spending is on necessities (groceries, bills, healthcare), which limits how much can realistically be cut.")
            if feasibility == "Ambitious":
                cons.append("Even realistic cuts across your top categories don't fully cover a 6-month timeline - a longer timeline or a smaller target would be more comfortable.")
        else:
            cons.append("There's no categorized spending to point to yet - contributions would need to come from general budgeting rather than a specific cut.")

        pros.append(f"A 6-month timeline only needs {monthly_6mo:.2f}/month; a 12-month timeline needs just {monthly_12mo:.2f}/month.")
        cons.append("Like any goal, unexpected expenses can slow progress unless contributions are automated (fixed monthly auto-save).")

        lines = [
            f"**Feasibility study — \"{goal_name}\", target {target_amount:.2f}**",
            "",
            f"Funding from: {source_account.nickname} (currently {balance:.2f})",
            f"Feasibility: **{feasibility}**",
            "",
            "**Pros:**",
        ]
        for p in pros:
            lines.append(f"- {p}")
        lines.append("")
        lines.append("**Cons:**")
        for c in cons:
            lines.append(f"- {c}")
        lines.append("")
        lines.append(
            f"Suggested timelines: 3 months = {monthly_3mo:.2f}/month · 6 months = {monthly_6mo:.2f}/month · "
            f"12 months = {monthly_12mo:.2f}/month."
        )
        lines.append("")
        lines.append("Want me to go ahead and set this up?")

        return "\n".join(lines)

    # Step two: client already confirmed - actually create the pending action.
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


async def set_goal_savings_plan(
    ctx: RunContext[ClientAgentDeps],
    goal_name: str,
    mode: str,
    fixed_monthly_amount: float | None = None,
) -> str:
    """Set up or change how a savings goal gets funded each month.
    mode should be 'fixed' (auto-save a set amount on the 1st of each
    month, no client action needed) or 'variable' (the client gets a
    reminder each month and contributes manually). If mode is 'fixed',
    fixed_monthly_amount is required. This takes effect immediately -
    it's a settings change, not a money transfer, so it doesn't need
    separate confirmation."""
    from app.models.models import SavingsGoal, ContributionMode
    from decimal import Decimal

    if mode not in ("fixed", "variable"):
        return "The savings plan mode should be either 'fixed' (auto-save a set amount monthly) or 'variable' (manual, with a monthly reminder)."
    if mode == "fixed" and not fixed_monthly_amount:
        return "For a fixed monthly plan, I need the amount to auto-save each month."

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

    goal.contribution_mode = ContributionMode.fixed if mode == "fixed" else ContributionMode.variable
    goal.fixed_monthly_amount = Decimal(str(fixed_monthly_amount)) if mode == "fixed" else None
    await ctx.deps.db.flush()

    if mode == "fixed":
        return (
            f"Done - '{goal.name}' will now auto-save {fixed_monthly_amount} on the 1st of each month, "
            f"moved automatically from its funding account. No action needed on your end each month."
        )
    return (
        f"Done - '{goal.name}' is now on a variable plan. You'll get a reminder on the 1st of each month "
        f"and can tell me how much to contribute that month."
    )


async def get_account_statement(
    ctx: RunContext[ClientAgentDeps],
    account_type: str | None = None,
    account_nickname: str | None = None,
) -> str:
    """Generate (or pull the most recent) statement for one of the
    client's accounts and make it downloadable. Use this whenever the
    client wants a statement, wants to download their statement as a
    PDF, or asks about their statement history. This creates a fresh
    snapshot covering the current month to date - it does NOT need
    separate confirmation, since it doesn't move any money."""
    from app.models.models import Statement
    from app.routers.statements import _generate_statement_for_account

    account, err = await _resolve_own_account(ctx, account_type, account_nickname)
    if err:
        return err

    statement = await _generate_statement_for_account(ctx.deps.db, account)

    period = f"{statement.period_start.strftime('%b %d')} - {statement.period_end.strftime('%b %d, %Y')}"
    return (
        f"Here's your statement for {account.nickname} ({period}):\n"
        f"Opening balance: {statement.opening_balance} {statement.currency}\n"
        f"Closing balance: {statement.closing_balance} {statement.currency}\n"
        f"Total deposits: {statement.total_deposits} {statement.currency}\n"
        f"Total withdrawals: {statement.total_withdrawals} {statement.currency}\n\n"
        f"Statement ID: {statement.id}"
    )


async def get_my_loans(ctx: RunContext[ClientAgentDeps]) -> str:
    """Check the client's loans - status, remaining balance, monthly
    payment, and next payment due date. Use this whenever the client asks
    about a loan, how much they still owe, or when their next payment is."""
    from app.models.models import Loan, Account

    result = await ctx.deps.db.execute(select(Loan).where(Loan.client_id == ctx.deps.user_id))
    loans = result.scalars().all()
    if not loans:
        return "You don't have any loans."

    lines = []
    for loan in loans:
        currency = "USD"
        if loan.disbursement_account_id:
            acc_result = await ctx.deps.db.execute(select(Account).where(Account.id == loan.disbursement_account_id))
            acc = acc_result.scalar_one_or_none()
            if acc:
                currency = acc.currency

        if loan.status.value == "pending":
            lines.append(f"{loan.amount} {currency} loan ({loan.purpose or 'no purpose given'}) - pending review, rate not yet set.")
        elif loan.status.value == "rejected":
            lines.append(f"{loan.amount} {currency} loan - rejected.")
        elif loan.status.value == "active":
            due = loan.next_payment_due.strftime("%b %d, %Y") if loan.next_payment_due else "unknown"
            lines.append(
                f"{loan.amount} {currency} loan at {loan.interest_rate}% - {loan.remaining_balance} {currency} remaining, "
                f"{loan.monthly_payment} {currency}/month, next payment due {due}."
            )
        elif loan.status.value == "closed":
            lines.append(f"{loan.amount} {currency} loan - paid off in full.")

    return "\n".join(lines)


async def propose_loan_payment(
    ctx: RunContext[ClientAgentDeps],
    amount: float,
    loan_index: int = 1,
) -> str:
    """Propose an extra/early payment toward one of the client's active
    loans, on top of their regular auto-debited monthly payment. Use
    get_my_loans first if the client has more than one loan so you can
    ask which one they mean; loan_index is 1 for their first/only loan,
    2 for the second, etc., in the order get_my_loans lists them. This
    does NOT execute immediately - the client must confirm."""
    from app.models.models import Loan, LoanStatus

    result = await ctx.deps.db.execute(
        select(Loan).where(Loan.client_id == ctx.deps.user_id, Loan.status == LoanStatus.active)
    )
    active_loans = result.scalars().all()
    if not active_loans:
        return "You don't have any active loans to pay toward."
    if loan_index < 1 or loan_index > len(active_loans):
        return f"You have {len(active_loans)} active loan(s). Please pick a valid one."

    loan = active_loans[loan_index - 1]
    if amount > float(loan.remaining_balance):
        return f"That's more than the remaining balance of {loan.remaining_balance} - the max payment right now is {loan.remaining_balance}."

    action = AgentActionLog(
        conversation_id=ctx.deps.conversation_id,
        tool_name="loan_repayment",
        input=json.dumps({"loan_id": loan.id, "amount": str(amount)}),
        status=AgentActionStatus.pending_approval,
    )
    ctx.deps.db.add(action)
    await ctx.deps.db.flush()

    return (
        f"I've prepared a payment of {amount} toward your loan (remaining balance {loan.remaining_balance}). "
        f"This hasn't been executed yet - please confirm using action id {action.id}."
    )