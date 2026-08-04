from pydantic import BaseModel, Field
from decimal import Decimal
from datetime import datetime
from app.models.models import LoanStatus


class LoanRequest(BaseModel):
    amount: Decimal = Field(gt=0)
    interest_rate: Decimal = Field(gt=0)
    term_months: int = Field(gt=0)


class LoanOut(BaseModel):
    id: str
    client_id: str
    amount: Decimal
    interest_rate: Decimal
    term_months: int
    status: LoanStatus
    approved_by: str | None
    created_at: datetime

    class Config:
        from_attributes = True