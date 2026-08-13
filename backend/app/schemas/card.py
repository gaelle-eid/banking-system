from pydantic import BaseModel
from datetime import datetime
from app.models.models import CardType, CardStatus, CardTier


class CardRequest(BaseModel):
    account_id: str
    type: CardType
    tier: CardTier = CardTier.standard


class CardOut(BaseModel):
    id: str
    account_id: str
    masked_number: str
    type: CardType
    tier: CardTier
    status: CardStatus
    expiry_date: datetime
    activated_at: datetime | None
    created_at: datetime

    class Config:
        from_attributes = True