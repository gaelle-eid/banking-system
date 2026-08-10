from pydantic import BaseModel, Field
from decimal import Decimal
from datetime import datetime
from app.models.models import ContributionMode


class SavingsGoalOut(BaseModel):
    id: str
    client_id: str
    name: str
    target_amount: Decimal
    goal_account_id: str | None
    source_account_id: str | None
    contribution_mode: ContributionMode | None
    fixed_monthly_amount: Decimal | None
    active: bool
    created_at: datetime

    class Config:
        from_attributes = True