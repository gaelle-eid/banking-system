from pydantic import BaseModel
from decimal import Decimal
from datetime import datetime
from app.models.models import CardType, CardStatus, CardTier


class CardRequest(BaseModel):
    account_id: str
    type: CardType
    tier: CardTier = CardTier.standard


class CardOut(BaseModel):
    id: str
    account_id: str
    account_nickname: str | None = None
    masked_number: str
    type: CardType
    tier: CardTier
    status: CardStatus
    expiry_date: datetime
    activated_at: datetime | None
    frozen: bool
    created_at: datetime

    class Config:
        from_attributes = True


class CardTierDetail(BaseModel):
    atm_daily_limit: Decimal
    annual_fee: Decimal
    rewards: str
    foreign_fee: str
    perks: str


class CardTierInfoOut(BaseModel):
    standard: CardTierDetail
    cashback: CardTierDetail
    travel: CardTierDetail
    premium: CardTierDetail