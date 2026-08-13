from pydantic import BaseModel, Field
from decimal import Decimal
from datetime import datetime
from app.models.models import FundingSourceStatus


class FundingSourceCreate(BaseModel):
    bank_name: str = Field(min_length=1, max_length=100)
    account_number: str = Field(min_length=4, max_length=34)


class FundingSourceOut(BaseModel):
    id: str
    bank_name: str
    masked_account_number: str
    status: FundingSourceStatus
    created_at: datetime
    verified_at: datetime | None

    class Config:
        from_attributes = True


class FundingSourceCreatedOut(FundingSourceOut):
    """Returned only once, right after creation. In a real bank these two
    amounts would be sent to the external account and checked there - since
    there's no real external bank here, we surface them directly so the
    verification flow can still be demonstrated end-to-end."""
    demo_micro_deposits: list[Decimal]


class FundingSourceVerify(BaseModel):
    amount_1: Decimal = Field(ge=0, le=0.99)
    amount_2: Decimal = Field(ge=0, le=0.99)