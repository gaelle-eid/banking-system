from pydantic import BaseModel
from decimal import Decimal
from datetime import datetime


class StatementTransactionLine(BaseModel):
    date: str
    type: str
    description: str
    amount: Decimal
    running_balance: Decimal


class StatementOut(BaseModel):
    id: str
    account_id: str
    period_start: datetime
    period_end: datetime
    opening_balance: Decimal | None
    closing_balance: Decimal | None
    total_deposits: Decimal | None
    total_withdrawals: Decimal | None
    currency: str | None
    transactions_snapshot: list[StatementTransactionLine] | None
    generated_at: datetime

    class Config:
        from_attributes = True