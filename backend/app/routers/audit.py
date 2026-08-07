from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from datetime import datetime

from app.core.database import get_db
from app.core.deps import require_role
from app.models.models import AuditLog, User, UserRole
from app.schemas.audit import AuditLogOut

router = APIRouter(prefix="/audit-logs", tags=["audit"])


@router.get("", response_model=list[AuditLogOut], dependencies=[Depends(require_role(UserRole.employee, UserRole.admin))])
async def list_audit_logs(
    actor_id: str | None = Query(None),
    entity_type: str | None = Query(None),
    since: datetime | None = Query(None),
    db: AsyncSession = Depends(get_db),
):
    query = select(AuditLog)
    if actor_id:
        query = query.where(AuditLog.actor_id == actor_id)
    if entity_type:
        query = query.where(AuditLog.entity_type == entity_type)
    if since:
        query = query.where(AuditLog.created_at >= since)
    query = query.order_by(AuditLog.created_at.desc())

    result = await db.execute(query)
    logs = result.scalars().all()

    output = []
    for log in logs:
        user_result = await db.execute(select(User).where(User.id == log.actor_id))
        user = user_result.scalar_one_or_none()
        log_out = AuditLogOut.model_validate(log)
        log_out.actor_name = user.full_name if user else "Unknown"
        output.append(log_out)

    return output