from pydantic import BaseModel
from datetime import datetime


class StatementOut(BaseModel):
    id: str
    account_id: str
    period_start: datetime
    period_end: datetime
    generated_at: datetime

    class Config:
        from_attributes = True