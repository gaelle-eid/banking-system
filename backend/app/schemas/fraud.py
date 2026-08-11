from pydantic import BaseModel
from datetime import datetime
from app.models.models import FraudFlagSeverity, FraudFlagStatus


class FraudFlagOut(BaseModel):
    id: str
    transaction_id: str
    account_id: str
    reason: str
    severity: FraudFlagSeverity
    status: FraudFlagStatus
    reviewed_by: str | None
    notes: str | None
    created_at: datetime

    class Config:
        from_attributes = True


class FraudDecisionRequest(BaseModel):
    notes: str | None = None