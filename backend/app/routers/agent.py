from fastapi import APIRouter, Depends

from app.core.database import get_db
from app.core.deps import get_current_user
from app.models.models import User, AgentType, AgentMessageRole
from app.schemas.agent import ChatRequest, ChatResponse
from app.agents.client_agent import client_agent
from app.agents.deps import ClientAgentDeps
from app.agents.memory import get_or_create_conversation, save_message
from sqlalchemy.ext.asyncio import AsyncSession

router = APIRouter(prefix="/agent/client", tags=["client-agent"])


@router.post("/chat", response_model=ChatResponse)
async def chat_with_client_agent(
    payload: ChatRequest,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    conversation = await get_or_create_conversation(db, current_user.id, AgentType.client)

    deps = ClientAgentDeps(db=db, user_id=current_user.id)
    result = await client_agent.run(payload.message, deps=deps)

    await save_message(db, conversation.id, AgentMessageRole.user, payload.message)
    await save_message(db, conversation.id, AgentMessageRole.assistant, result.output)
    await db.commit()

    return ChatResponse(reply=result.output, conversation_id=conversation.id)