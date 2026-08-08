from pydantic import BaseModel, Field
from decimal import Decimal
from datetime import datetime
from app.models.models import TransactionType, TransactionStatus


class DepositRequest(BaseModel):
    account_id: str
    amount: Decimal = Field(gt=0)


class WithdrawalRequest(BaseModel):
    account_id: str
    amount: Decimal = Field(gt=0)


class TransferRequest(BaseModel):
    from_account_id: str
    to_account_id: str
    amount: Decimal = Field(gt=0)


class TransactionOut(BaseModel):
    id: str
    account_id: str
    type: TransactionType
    amount: Decimal
    transfer_group_id: str | None
    status: TransactionStatus
    created_at: datetime

    class Config:
        from_attributes = True


class PhoneTransferInitiateRequest(BaseModel):
    from_account_id: str
    to_phone: str
    amount: Decimal = Field(gt=0)


class PhoneTransferConfirmRequest(BaseModel):
    verification_id: str
    otp: str