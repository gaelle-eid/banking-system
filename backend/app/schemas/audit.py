from pydantic import BaseModel
from datetime import datetime
from typing import Any


class AuditLogOut(BaseModel):
    id: str
    actor_id: str
    actor_name: str | None = None
    action: str
    entity_type: str
    entity_id: str
    details: dict[str, Any] | None
    created_at: datetime

    class Config:
        from_attributes = True