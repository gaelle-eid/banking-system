from pydantic import BaseModel
from datetime import datetime
from app.models.models import ApprovalEntityType, ApprovalStatus


class ApprovalOut(BaseModel):
    id: str
    entity_type: ApprovalEntityType
    entity_id: str
    requested_by: str
    requested_by_name: str | None = None
    requested_by_email: str | None = None
    approved_by: str | None
    status: ApprovalStatus
    notes: str | None
    created_at: datetime
    details: dict | None = None  # entity-specific: loan amount/term/purpose, or card type/tier/account
    client_context: dict | None = None  # client history/risk: account age, verification, existing loans/cards, fraud flags
    requires_admin: bool = False  # true when this approval exceeds a threshold requiring admin sign-off

    class Config:
        from_attributes = True


class ApprovalActionRequest(BaseModel):
    notes: str | None = None
    interest_rate: float | None = None  # required when approving a loan - the bank sets the rate