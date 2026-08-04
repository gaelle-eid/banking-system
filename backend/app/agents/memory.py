from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from app.models.models import AgentConversation, AgentMessage, AgentType, AgentMessageRole


async def get_or_create_conversation(db: AsyncSession, user_id: str, agent_type: AgentType) -> AgentConversation:
    result = await db.execute(
        select(AgentConversation)
        .where(AgentConversation.user_id == user_id, AgentConversation.agent_type == agent_type)
        .order_by(AgentConversation.created_at.desc())
    )
    conversation = result.scalars().first()
    if conversation:
        return conversation

    conversation = AgentConversation(user_id=user_id, agent_type=agent_type)
    db.add(conversation)
    await db.flush()
    return conversation


async def load_history(db: AsyncSession, conversation_id: str) -> list[dict]:
    result = await db.execute(
        select(AgentMessage)
        .where(AgentMessage.conversation_id == conversation_id)
        .order_by(AgentMessage.created_at.asc())
    )
    messages = result.scalars().all()
    return [{"role": m.role.value, "content": m.content} for m in messages]


async def save_message(db: AsyncSession, conversation_id: str, role: AgentMessageRole, content: str):
    msg = AgentMessage(conversation_id=conversation_id, role=role, content=content)
    db.add(msg)