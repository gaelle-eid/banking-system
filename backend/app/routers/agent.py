import json
import uuid
from decimal import Decimal

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from app.core.database import get_db
from app.core.deps import get_current_user
from app.core.account_access import user_can_access_account
from app.core.exchange_rates import convert as convert_currency
from app.models.models import (
    User, AgentType, AgentMessageRole, AgentActionLog, AgentActionStatus, Account,
    Transaction, TransactionType, TransactionStatus, SavingsGoal,
)
from app.schemas.agent import ChatRequest, ChatResponse
from app.agents.client_agent import client_agent
from app.agents.deps import ClientAgentDeps
from app.agents.memory import get_or_create_conversation, load_message_history, save_turn

router = APIRouter(prefix="/agent/client", tags=["client-agent"])


@router.post("/chat", response_model=ChatResponse)
async def chat_with_client_agent(
    payload: ChatRequest,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    conversation = await get_or_create_conversation(db, current_user.id, AgentType.client)
    history = await load_message_history(db, conversation.id)

    deps = ClientAgentDeps(db=db, user_id=current_user.id, conversation_id=conversation.id)
    result = await client_agent.run(payload.message, deps=deps, message_history=history)

    await save_turn(db, conversation.id, result.new_messages())
    await db.commit()

    return ChatResponse(reply=result.output, conversation_id=conversation.id)


@router.post("/actions/{action_id}/confirm")
async def confirm_agent_action(
    action_id: str,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(select(AgentActionLog).where(AgentActionLog.id == action_id))
    action = result.scalar_one_or_none()
    if not action:
        raise HTTPException(status_code=404, detail="Action not found")
    if action.status != AgentActionStatus.pending_approval:
        raise HTTPException(status_code=400, detail=f"Action is already {action.status.value}")

    if action.tool_name == "transfer":
        data = json.loads(action.input)
        from_result = await db.execute(select(Account).where(Account.id == data["from_account_id"]))
        from_account = from_result.scalar_one_or_none()
        if not from_account or not await user_can_access_account(db, current_user.id, from_account.id):
            raise HTTPException(status_code=403, detail="Not your account")

        to_result = await db.execute(select(Account).where(Account.id == data["to_account_id"]))
        to_account = to_result.scalar_one_or_none()
        if not to_account:
            raise HTTPException(status_code=404, detail="Destination account not found")

        amount = Decimal(data["amount"])
        if from_account.balance < amount:
            raise HTTPException(status_code=400, detail="Insufficient funds")

        group_id = str(uuid.uuid4())

        exchange_rate = None
        credit_amount = amount
        if from_account.currency != to_account.currency:
            try:
                credit_amount, exchange_rate = await convert_currency(amount, from_account.currency, to_account.currency)
            except ValueError as e:
                raise HTTPException(status_code=400, detail=str(e))
            except Exception:
                raise HTTPException(status_code=503, detail="Exchange rate service is temporarily unavailable, please try again")

        from_account.balance -= amount
        to_account.balance += credit_amount

        db.add(Transaction(
            account_id=from_account.id, type=TransactionType.transfer_debit,
            amount=amount, transfer_group_id=group_id,
            status=TransactionStatus.completed, initiated_by=current_user.id,
            exchange_rate=exchange_rate,
        ))
        db.add(Transaction(
            account_id=to_account.id, type=TransactionType.transfer_credit,
            amount=credit_amount, transfer_group_id=group_id,
            status=TransactionStatus.completed, initiated_by=current_user.id,
            exchange_rate=exchange_rate,
        ))

        action.status = AgentActionStatus.executed
        action.output = json.dumps({"transfer_group_id": group_id})
        await db.commit()
        return {"status": "executed", "transfer_group_id": group_id}


    if action.tool_name == "goal_contribution":
        data = json.loads(action.input)
        source_result = await db.execute(
            select(Account).where(Account.id == data["source_account_id"], Account.owner_id == current_user.id)
        )
        source_account = source_result.scalar_one_or_none()
        if not source_account:
            raise HTTPException(status_code=403, detail="Not your account")

        goal_account_result = await db.execute(select(Account).where(Account.id == data["goal_account_id"]))
        goal_account = goal_account_result.scalar_one_or_none()
        if not goal_account:
            raise HTTPException(status_code=404, detail="Goal account not found")

        amount = Decimal(data["amount"])
        if source_account.balance < amount:
            raise HTTPException(status_code=400, detail="Insufficient funds")

        group_id = str(uuid.uuid4())
        source_account.balance -= amount
        goal_account.balance += amount

        db.add(Transaction(
            account_id=source_account.id, type=TransactionType.transfer_debit,
            amount=amount, transfer_group_id=group_id,
            status=TransactionStatus.completed, initiated_by=current_user.id,
        ))
        db.add(Transaction(
            account_id=goal_account.id, type=TransactionType.transfer_credit,
            amount=amount, transfer_group_id=group_id,
            status=TransactionStatus.completed, initiated_by=current_user.id,
        ))

        action.status = AgentActionStatus.executed
        action.output = json.dumps({"transfer_group_id": group_id})
        await db.commit()
        return {"status": "executed", "goal_contribution": True, "amount": str(amount)}

    
    if action.tool_name == "create_savings_goal":
        import random

        data = json.loads(action.input)
        source_result = await db.execute(
            select(Account).where(Account.id == data["source_account_id"], Account.owner_id == current_user.id)
        )
        source_account = source_result.scalar_one_or_none()
        if not source_account:
            raise HTTPException(status_code=403, detail="Not your account")

        goal_account = Account(
            owner_id=current_user.id,
            account_number="".join(str(random.randint(0, 9)) for _ in range(10)),
            nickname=data["goal_name"],
            type="savings",
            currency=source_account.currency,
            balance=0,
        )
        db.add(goal_account)
        await db.flush()

        goal = SavingsGoal(
            client_id=current_user.id,
            name=data["goal_name"],
            target_amount=Decimal(data["target_amount"]),
            goal_account_id=goal_account.id,
            source_account_id=source_account.id,
        )
        db.add(goal)

        action.status = AgentActionStatus.executed
        action.output = json.dumps({"goal_id": goal.id, "goal_account_id": goal_account.id})
        await db.commit()
        return {"status": "executed", "goal_account_nickname": goal_account.nickname}

    if action.tool_name == "loan_repayment":
        from app.models.models import Loan, LoanStatus, Account, TransactionType, TransactionStatus

        data = json.loads(action.input)
        loan_result = await db.execute(select(Loan).where(Loan.id == data["loan_id"]))
        loan = loan_result.scalar_one_or_none()
        if not loan or loan.client_id != current_user.id:
            raise HTTPException(status_code=403, detail="Not your loan")
        if loan.status != LoanStatus.active:
            raise HTTPException(status_code=400, detail=f"This loan is {loan.status.value}, not active")

        account_result = await db.execute(select(Account).where(Account.id == loan.disbursement_account_id))
        account = account_result.scalar_one_or_none()
        if not account:
            raise HTTPException(status_code=400, detail="The linked account no longer exists")

        amount = Decimal(data["amount"])
        payment = min(amount, loan.remaining_balance)
        if account.balance < payment:
            raise HTTPException(status_code=400, detail="Insufficient funds for this payment")

        account.balance -= payment
        loan.remaining_balance -= payment

        db.add(Transaction(
            account_id=account.id, type=TransactionType.withdrawal,
            amount=payment, status=TransactionStatus.completed,
            initiated_by=current_user.id, source="Loan Repayment (via Assistant)",
        ))

        if loan.remaining_balance <= 0:
            loan.remaining_balance = Decimal("0")
            loan.status = LoanStatus.closed
            loan.next_payment_due = None

        action.status = AgentActionStatus.executed
        action.output = json.dumps({"remaining_balance": str(loan.remaining_balance)})
        await db.commit()
        return {"status": "executed", "loan_repayment": True, "amount": str(payment), "remaining_balance": str(loan.remaining_balance)}

    raise HTTPException(status_code=400, detail="Unknown action type")


@router.post("/actions/{action_id}/reject")
async def reject_agent_action(
    action_id: str,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(select(AgentActionLog).where(AgentActionLog.id == action_id))
    action = result.scalar_one_or_none()
    if not action:
        raise HTTPException(status_code=404, detail="Action not found")
    if action.status != AgentActionStatus.pending_approval:
        raise HTTPException(status_code=400, detail=f"Action is already {action.status.value}")

    action.status = AgentActionStatus.rejected
    await db.commit()
    return {"status": "rejected"}