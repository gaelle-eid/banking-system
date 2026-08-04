from pydantic import BaseModel
from decimal import Decimal
from datetime import datetime
from app.models.models import AccountType, AccountStatus


class AccountCreate(BaseModel):
    type: AccountType
    currency: str = "USD"


class AccountOut(BaseModel):
    id: str
    account_number: str
    type: AccountType
    balance: Decimal
    currency: str
    status: AccountStatus
    created_at: datetime

    class Config:
        from_attributes = True