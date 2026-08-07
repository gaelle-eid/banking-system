from pydantic import BaseModel
from datetime import datetime


class PendingRegistrationOut(BaseModel):
    id: str
    email: str
    full_name: str
    phone: str | None
    address: str | None
    national_id: str | None
    national_id_photo_path: str | None
    created_at: datetime

    class Config:
        from_attributes = True


class RegistrationDecisionRequest(BaseModel):
    notes: str | None = None