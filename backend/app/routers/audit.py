from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from datetime import datetime

from app.core.database import get_db
from app.core.deps import require_role
from app.models.models import AuditLog, UserRole
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
    return result.scalars().all()