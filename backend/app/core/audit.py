from sqlalchemy.ext.asyncio import AsyncSession
from app.models.models import AuditLog


async def log_action(db: AsyncSession, actor_id: str, action: str, entity_type: str, entity_id: str, details: dict | None = None):
    entry = AuditLog(
        actor_id=actor_id,
        action=action,
        entity_type=entity_type,
        entity_id=entity_id,
        details=details,
    )
    db.add(entry)

    