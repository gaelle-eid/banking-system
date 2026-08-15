from pydantic import BaseModel
from decimal import Decimal


class BankSummaryReport(BaseModel):
    total_accounts: int
    total_balance: Decimal  # USD-equivalent, converted across all currencies
    total_clients: int
    total_employees: int
    pending_approvals: int
    pending_registrations: int
    pending_fraud_flags: int
    high_severity_fraud_count: int
    transactions_today: int
    active_loans: int
    active_cards: int