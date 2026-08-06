import json
from pydantic_ai import RunContext
from sqlalchemy import select, func

from app.agents.deps import EmployeeAgentDeps
from app.models.models import (
    Approval, ApprovalStatus, ApprovalEntityType,
    Loan, Card, User, Account, Transaction,
    AgentActionLog, AgentActionStatus,
)


async def list_pending_approvals(ctx: RunContext[EmployeeAgentDeps], entity_type: str | None = None) -> str:
    """List pending approval requests (loans, cards). Optionally filter by
    entity_type ('loan' or 'card')."""
    query = select(Approval).where(Approval.status == ApprovalStatus.pending)
    if entity_type:
        query = query.where(Approval.entity_type == entity_type)
    query = query.order_by(Approval.created_at.asc())

    result = await ctx.deps.db.execute(query)
    approvals = result.scalars().all()

    if not approvals:
        return "There are no pending approvals right now."

    lines = []
    for a in approvals:
        requester_result = await ctx.deps.db.execute(select(User).where(User.id == a.requested_by))
        requester = requester_result.scalar_one_or_none()
        requester_name = requester.full_name if requester else "unknown"

        detail = ""
        if a.entity_type == ApprovalEntityType.loan:
            loan_result = await ctx.deps.db.execute(select(Loan).where(Loan.id == a.entity_id))
            loan = loan_result.scalar_one_or_none()
            if loan:
                detail = f"amount {loan.amount}, {loan.interest_rate}% over {loan.term_months} months"
        elif a.entity_type == ApprovalEntityType.card:
            card_result = await ctx.deps.db.execute(select(Card).where(Card.id == a.entity_id))
            card = card_result.scalar_one_or_none()
            if card:
                detail = f"{card.type.value} card"

        lines.append(
            f"[approval_id: {a.id}] {a.entity_type.value} request from {requester_name} - {detail} "
            f"(requested {a.created_at.date()})"
        )
    return "\n".join(lines)


async def summarize_client_activity(ctx: RunContext[EmployeeAgentDeps], client_email: str) -> str:
    """Summarize a client's accounts, balances, and recent transaction
    activity, looked up by their email."""
    result = await ctx.deps.db.execute(select(User).where(User.email == client_email))
    client = result.scalar_one_or_none()
    if not client:
        return "No client found with that email."

    result = await ctx.deps.db.execute(select(Account).where(Account.owner_id == client.id))
    accounts = result.scalars().all()
    if not accounts:
        return f"{client.full_name} has no accounts yet."

    lines = [f"Client: {client.full_name} ({client.email})"]
    total_balance = 0
    for acc in accounts:
        lines.append(f"- {acc.nickname or acc.type.value}: {acc.balance} {acc.currency} ({acc.status.value})")
        total_balance += float(acc.balance)

        tx_result = await ctx.deps.db.execute(
            select(Transaction)
            .where(Transaction.account_id == acc.id)
            .order_by(Transaction.created_at.desc())
            .limit(3)
        )
        recent = tx_result.scalars().all()
        for tx in recent:
            lines.append(f"    · {tx.created_at.date()} {tx.type.value} {tx.amount}")

    lines.append(f"Total across accounts: {total_balance}")
    return "\n".join(lines)


async def get_bank_summary(ctx: RunContext[EmployeeAgentDeps]) -> str:
    """Get a live summary of bank-wide numbers: total accounts, balance,
    clients, employees, pending approvals, today's transactions, active
    loans and cards."""
    from app.models.models import LoanStatus, CardStatus, UserRole
    from datetime import datetime

    total_accounts = (await ctx.deps.db.execute(select(func.count(Account.id)))).scalar() or 0
    total_balance = (await ctx.deps.db.execute(select(func.coalesce(func.sum(Account.balance), 0)))).scalar() or 0
    total_clients = (await ctx.deps.db.execute(select(func.count(User.id)).where(User.role == UserRole.client))).scalar() or 0
    pending = (await ctx.deps.db.execute(select(func.count(Approval.id)).where(Approval.status == ApprovalStatus.pending))).scalar() or 0

    start_of_day = datetime.utcnow().replace(hour=0, minute=0, second=0, microsecond=0)
    tx_today = (await ctx.deps.db.execute(select(func.count(Transaction.id)).where(Transaction.created_at >= start_of_day))).scalar() or 0

    active_loans = (await ctx.deps.db.execute(select(func.count(Loan.id)).where(Loan.status == LoanStatus.active))).scalar() or 0
    active_cards = (await ctx.deps.db.execute(select(func.count(Card.id)).where(Card.status == CardStatus.active))).scalar() or 0

    return (
        f"Bank summary: {total_accounts} accounts, {total_balance} total balance, "
        f"{total_clients} clients, {pending} pending approvals, "
        f"{tx_today} transactions today, {active_loans} active loans, {active_cards} active cards."
    )


async def propose_approval_decision(
    ctx: RunContext[EmployeeAgentDeps],
    approval_id: str,
    decision: str,
    notes: str | None = None,
) -> str:
    """Propose approving or rejecting a pending request (loan or card).
    decision must be 'approve' or 'reject'. This does NOT execute the
    decision immediately - it creates a pending action the employee must
    confirm separately before it takes effect."""

    if decision not in ("approve", "reject"):
        return "Decision must be either 'approve' or 'reject'."

    result = await ctx.deps.db.execute(select(Approval).where(Approval.id == approval_id))
    approval = result.scalar_one_or_none()
    if not approval:
        return "I couldn't find an approval with that id."
    if approval.status != ApprovalStatus.pending:
        return f"This request is already {approval.status.value}, nothing to do."

    action = AgentActionLog(
        conversation_id=ctx.deps.conversation_id,
        tool_name="approval_decision",
        input=json.dumps({"approval_id": approval_id, "decision": decision, "notes": notes}),
        status=AgentActionStatus.pending_approval,
    )
    ctx.deps.db.add(action)
    await ctx.deps.db.flush()

    return (
        f"I've prepared a decision to {decision} the {approval.entity_type.value} request "
        f"(approval id {approval_id}). This hasn't been applied yet - "
        f"please confirm it using action id {action.id}."
    )