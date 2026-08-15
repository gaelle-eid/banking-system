from pydantic import BaseModel, Field
from decimal import Decimal
from datetime import datetime
from app.models.models import TransactionType, TransactionStatus, TransactionCategory


class DepositRequest(BaseModel):
    account_id: str
    amount: Decimal = Field(gt=0)
    funding_source_id: str


class WithdrawalRequest(BaseModel):
    account_id: str
    amount: Decimal = Field(gt=0)
    method: str  # "atm" / "branch_teller" / "cash_back" / "external_wallet"
    card_id: str | None = None  # required when method is "atm"
    category: TransactionCategory | None = None
    wallet_provider: str | None = None  # required when method is "external_wallet", e.g. "Whish Money"
    wallet_phone: str | None = None  # required when method is "external_wallet"


class TransferRequest(BaseModel):
    from_account_id: str
    to_account_id: str
    amount: Decimal = Field(gt=0)
    category: TransactionCategory | None = None


class TransactionOut(BaseModel):
    id: str
    account_id: str
    type: TransactionType
    amount: Decimal
    transfer_group_id: str | None
    status: TransactionStatus
    exchange_rate: Decimal | None = None
    source: str | None = None
    method: str | None = None
    category: TransactionCategory | None = None
    created_at: datetime

    class Config:
        from_attributes = True


class PhoneTransferInitiateRequest(BaseModel):
    from_account_id: str
    to_phone: str
    amount: Decimal = Field(gt=0)


class PhoneTransferInitiateOut(BaseModel):
    verification_id: str
    recipient_name: str
    message: str


class PhoneTransferConfirmRequest(BaseModel):
    verification_id: str
    otp: str