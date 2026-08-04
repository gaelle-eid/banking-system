from dataclasses import dataclass
from sqlalchemy.ext.asyncio import AsyncSession

from dataclasses import dataclass
from sqlalchemy.ext.asyncio import AsyncSession

@dataclass
class ClientAgentDeps:
    db: AsyncSession
    user_id: str





@dataclass
class ClientAgentDeps:
    db: AsyncSession
    user_id: str
    conversation_id: str