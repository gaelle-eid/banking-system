import json
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from pydantic_ai.messages import ModelMessagesTypeAdapter, ModelMessage

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


async def load_message_history(db: AsyncSession, conversation_id: str) -> list[ModelMessage]:
    """Load prior turns as PydanticAI ModelMessage objects, for passing into Agent.run()."""
    result = await db.execute(
        select(AgentMessage)
        .where(AgentMessage.conversation_id == conversation_id)
        .order_by(AgentMessage.created_at.asc())
    )
    rows = result.scalars().all()

    history: list[ModelMessage] = []
    for row in rows:
        try:
            parsed = json.loads(row.content)
            messages = ModelMessagesTypeAdapter.validate_python(parsed)
            history.extend(messages)
        except (json.JSONDecodeError, Exception):
            continue
    return history


async def save_turn(db: AsyncSession, conversation_id: str, new_messages: list[ModelMessage]):
    """Save one turn's worth of new messages (user + assistant + any tool calls) as a single row."""
    serialized = ModelMessagesTypeAdapter.dump_python(new_messages, mode="json")
    msg = AgentMessage(
        conversation_id=conversation_id,
        role=AgentMessageRole.assistant,  # role field kept for schema compat; content holds the full turn
        content=json.dumps(serialized),
    )
    db.add(msg)