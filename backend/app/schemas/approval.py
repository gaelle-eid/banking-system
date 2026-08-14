from pydantic import BaseModel
from datetime import datetime
from app.models.models import ApprovalEntityType, ApprovalStatus


class ApprovalOut(BaseModel):
    id: str
    entity_type: ApprovalEntityType
    entity_id: str
    requested_by: str
    approved_by: str | None
    status: ApprovalStatus
    notes: str | None
    created_at: datetime

    class Config:
        from_attributes = True


class ApprovalActionRequest(BaseModel):
    notes: str | None = None
    interest_rate: float | None = None  # required when approving a loan - the bank sets the rate