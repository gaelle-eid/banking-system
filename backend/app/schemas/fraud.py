from pydantic import BaseModel
from datetime import datetime
from decimal import Decimal
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
    client_name: str | None = None
    client_email: str | None = None
    account_label: str | None = None  # nickname + masked account number
    transaction_details: dict | None = None  # amount, type, currency, created_at, source/method
    recent_transactions: list[dict] = []  # the account's other recent activity, for pattern context
    related_pending_flags: list[dict] = []  # other pending flags on the SAME client - lightweight case linking

    class Config:
        from_attributes = True


class FraudDecisionRequest(BaseModel):
    notes: str | None = None