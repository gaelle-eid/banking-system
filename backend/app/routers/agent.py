import json
import uuid
from decimal import Decimal

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from app.core.database import get_db
from app.core.deps import get_current_user
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
        from_result = await db.execute(
            select(Account).where(Account.id == data["from_account_id"], Account.owner_id == current_user.id)
        )
        from_account = from_result.scalar_one_or_none()
        if not from_account:
            raise HTTPException(status_code=403, detail="Not your account")

        to_result = await db.execute(select(Account).where(Account.id == data["to_account_id"]))
        to_account = to_result.scalar_one_or_none()
        if not to_account:
            raise HTTPException(status_code=404, detail="Destination account not found")

        amount = Decimal(data["amount"])
        if from_account.balance < amount:
            raise HTTPException(status_code=400, detail="Insufficient funds")

        group_id = str(uuid.uuid4())
        from_account.balance -= amount
        to_account.balance += amount

        db.add(Transaction(
            account_id=from_account.id, type=TransactionType.transfer_debit,
            amount=amount, transfer_group_id=group_id,
            status=TransactionStatus.completed, initiated_by=current_user.id,
        ))
        db.add(Transaction(
            account_id=to_account.id, type=TransactionType.transfer_credit,
            amount=amount, transfer_group_id=group_id,
            status=TransactionStatus.completed, initiated_by=current_user.id,
        ))

        action.status = AgentActionStatus.executed
        action.output = json.dumps({"transfer_group_id": group_id})
        await db.commit()
        return {"status": "executed", "transfer_group_id": group_id}

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