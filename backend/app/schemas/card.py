from pydantic import BaseModel
from datetime import datetime
from app.models.models import CardType, CardStatus


class CardRequest(BaseModel):
    account_id: str
    type: CardType


class CardOut(BaseModel):
    id: str
    account_id: str
    masked_number: str
    type: CardType
    status: CardStatus
    expiry_date: datetime
    created_at: datetime

    class Config:
        from_attributes = True