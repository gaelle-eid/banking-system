from pydantic import BaseModel
from decimal import Decimal


class BankSummaryReport(BaseModel):
    total_accounts: int
    total_balance: Decimal
    total_clients: int
    total_employees: int
    pending_approvals: int
    transactions_today: int
    active_loans: int
    active_cards: int