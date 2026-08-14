from pydantic import BaseModel, Field
from decimal import Decimal
from datetime import datetime
from app.models.models import LoanStatus


class LoanRequest(BaseModel):
    amount: Decimal = Field(gt=0)
    term_months: int = Field(gt=0)
    purpose: str | None = None
    disbursement_account_id: str  # which of the client's accounts receives the funds if approved


class LoanRepaymentRequest(BaseModel):
    amount: Decimal = Field(gt=0)


class LoanOut(BaseModel):
    id: str
    client_id: str
    amount: Decimal
    interest_rate: Decimal | None  # set by the bank at approval, null while pending
    term_months: int
    purpose: str | None
    disbursement_account_id: str | None
    disbursed_at: datetime | None
    total_repayment: Decimal | None
    monthly_payment: Decimal | None
    remaining_balance: Decimal | None
    next_payment_due: datetime | None
    status: LoanStatus
    approved_by: str | None
    created_at: datetime

    class Config:
        from_attributes = True