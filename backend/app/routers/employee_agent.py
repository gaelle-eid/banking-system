import json

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from app.core.database import get_db
from app.core.deps import get_current_user, require_role
from app.core.audit import log_action
from app.models.models import (
    User, UserRole, AgentType, AgentActionLog, AgentActionStatus,
    Approval, ApprovalStatus, ApprovalEntityType, Loan, LoanStatus, Card, CardStatus,
)
from app.schemas.employee_agent import EmployeeChatRequest, EmployeeChatResponse
from app.agents.employee_agent import employee_agent
from app.agents.deps import EmployeeAgentDeps
from app.agents.memory import get_or_create_conversation, load_message_history, save_turn

router = APIRouter(prefix="/agent/employee", tags=["employee-agent"])


@router.post("/chat", response_model=EmployeeChatResponse, dependencies=[Depends(require_role(UserRole.employee, UserRole.admin))])
async def chat_with_employee_agent(
    payload: EmployeeChatRequest,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    conversation = await get_or_create_conversation(db, current_user.id, AgentType.employee)
    history = await load_message_history(db, conversation.id)

    deps = EmployeeAgentDeps(db=db, user_id=current_user.id, conversation_id=conversation.id)
    result = await employee_agent.run(payload.message, deps=deps, message_history=history)

    await save_turn(db, conversation.id, result.new_messages())
    await db.commit()

    return EmployeeChatResponse(reply=result.output, conversation_id=conversation.id)


@router.post("/actions/{action_id}/confirm", dependencies=[Depends(require_role(UserRole.employee, UserRole.admin))])
async def confirm_employee_action(
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

    if action.tool_name == "approval_decision":
        data = json.loads(action.input)
        approval_result = await db.execute(select(Approval).where(Approval.id == data["approval_id"]))
        approval = approval_result.scalar_one_or_none()
        if not approval:
            raise HTTPException(status_code=404, detail="Approval not found")
        if approval.status != ApprovalStatus.pending:
            raise HTTPException(status_code=400, detail=f"Approval is already {approval.status.value}")

        decision = data["decision"]
        notes = data.get("notes")

        if decision == "approve":
            if approval.entity_type == ApprovalEntityType.loan:
                loan_result = await db.execute(select(Loan).where(Loan.id == approval.entity_id))
                loan = loan_result.scalar_one_or_none()
                if loan:
                    loan.status = LoanStatus.active
                    loan.approved_by = current_user.id
            elif approval.entity_type == ApprovalEntityType.card:
                card_result = await db.execute(select(Card).where(Card.id == approval.entity_id))
                card = card_result.scalar_one_or_none()
                if card:
                    card.status = CardStatus.active
            approval.status = ApprovalStatus.approved
        else:
            if approval.entity_type == ApprovalEntityType.loan:
                loan_result = await db.execute(select(Loan).where(Loan.id == approval.entity_id))
                loan = loan_result.scalar_one_or_none()
                if loan:
                    loan.status = LoanStatus.rejected
            elif approval.entity_type == ApprovalEntityType.card:
                card_result = await db.execute(select(Card).where(Card.id == approval.entity_id))
                card = card_result.scalar_one_or_none()
                if card:
                    card.status = CardStatus.blocked
            approval.status = ApprovalStatus.rejected

        approval.approved_by = current_user.id
        approval.notes = notes

        await log_action(
            db, current_user.id, decision, approval.entity_type.value, approval.entity_id,
            details={"approval_id": approval.id, "notes": notes, "via": "agent"},
        )

        action.status = AgentActionStatus.executed
        action.output = json.dumps({"approval_id": approval.id, "decision": decision})
        await db.commit()
        return {"status": "executed", "decision": decision, "approval_id": approval.id}

    raise HTTPException(status_code=400, detail="Unknown action type")


@router.post("/actions/{action_id}/reject", dependencies=[Depends(require_role(UserRole.employee, UserRole.admin))])
async def reject_employee_action(
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