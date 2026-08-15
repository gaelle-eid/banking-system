import uuid
import enum
from datetime import datetime

from sqlalchemy import (
    Column, String, Numeric, ForeignKey, DateTime, Enum, Text, JSON, Boolean
)
from pgvector.sqlalchemy import Vector
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship, declarative_base

Base = declarative_base()


def gen_uuid():
    return str(uuid.uuid4())


# ---------- Enums ----------

class UserRole(str, enum.Enum):
    client = "client"
    employee = "employee"
    admin = "admin"


class AccountType(str, enum.Enum):
    checking = "checking"
    savings = "savings"


class CurrencyCode(str, enum.Enum):
    USD = "USD"
    EUR = "EUR"
    GBP = "GBP"
    LBP = "LBP"
    JOD = "JOD"


class JointOwnerStatus(str, enum.Enum):
    pending = "pending"
    accepted = "accepted"
    declined = "declined"

class FundingSourceStatus(str, enum.Enum):
    pending_verification = "pending_verification"
    verified = "verified"
    failed = "failed"

class AccountStatus(str, enum.Enum):
    active = "active"
    frozen = "frozen"
    closed = "closed"


class TransactionType(str, enum.Enum):
    deposit = "deposit"
    withdrawal = "withdrawal"
    transfer_debit = "transfer_debit"
    transfer_credit = "transfer_credit"


class TransactionCategory(str, enum.Enum):
    dining = "dining"
    groceries = "groceries"
    travel = "travel"
    entertainment = "entertainment"
    bills_utilities = "bills_utilities"
    shopping = "shopping"
    healthcare = "healthcare"
    transfer_to_person = "transfer_to_person"
    cash_withdrawal = "cash_withdrawal"
    income = "income"
    loan_repayment = "loan_repayment"
    savings = "savings"
    other = "other"

class TransactionStatus(str, enum.Enum):
    pending = "pending"
    completed = "completed"
    rejected = "rejected"


class LoanStatus(str, enum.Enum):
    pending = "pending"
    approved = "approved"
    rejected = "rejected"
    active = "active"
    closed = "closed"


class CardType(str, enum.Enum):
    debit = "debit"
    credit = "credit"

class CardTier(str, enum.Enum):
    standard = "standard"
    cashback = "cashback"
    travel = "travel"
    premium = "premium"

class CardStatus(str, enum.Enum):
    pending = "pending"
    active = "active"
    blocked = "blocked"
    expired = "expired"


class ApprovalEntityType(str, enum.Enum):
    transaction = "transaction"
    loan = "loan"
    card = "card"
    agent_action = "agent_action"


class ApprovalStatus(str, enum.Enum):
    pending = "pending"
    approved = "approved"
    rejected = "rejected"


class AgentType(str, enum.Enum):
    client = "client"
    employee = "employee"


class AgentMessageRole(str, enum.Enum):
    user = "user"
    assistant = "assistant"
    tool = "tool"


class AgentActionStatus(str, enum.Enum):
    pending_approval = "pending_approval"
    approved = "approved"
    executed = "executed"
    rejected = "rejected"

class EmployeeStatus(str, enum.Enum):
    active = "active"
    on_leave = "on_leave"
    terminated = "terminated"


class RegistrationStatus(str, enum.Enum):
    pending_review = "pending_review"
    approved = "approved"
    rejected = "rejected"

# ---------- Core ----------

class User(Base):
    __tablename__ = "users"

    id = Column(UUID(as_uuid=False), primary_key=True, default=gen_uuid)
    email = Column(String, unique=True, nullable=False, index=True)
    password_hash = Column(String, nullable=False)
    full_name = Column(String, nullable=False)
    phone = Column(String, nullable=True)
    phone_verified = Column(Boolean, default=False, nullable=False)
    phone_otp = Column(String, nullable=True)
    phone_otp_expires_at = Column(DateTime, nullable=True)
    date_of_birth = Column(DateTime, nullable=True)
    address = Column(String, nullable=True)
    national_id = Column(String, nullable=True)
    national_id_photo_path = Column(String, nullable=True)
    role = Column(Enum(UserRole), nullable=False)
    is_verified = Column(Boolean, default=False, nullable=False)
    registration_status = Column(Enum(RegistrationStatus), default=RegistrationStatus.pending_review, nullable=False)
    verification_token = Column(String, nullable=True)
    last_login_at = Column(DateTime, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)

    accounts = relationship("Account", back_populates="owner")


class Account(Base):
    __tablename__ = "accounts"

    id = Column(UUID(as_uuid=False), primary_key=True, default=gen_uuid)
    owner_id = Column(UUID(as_uuid=False), ForeignKey("users.id"), nullable=False)
    account_number = Column(String, unique=True, nullable=False)
    nickname = Column(String, nullable=True)
    type = Column(Enum(AccountType), nullable=False)
    balance = Column(Numeric(14, 2), nullable=False, default=0)
    currency = Column(String, default="USD")
    status = Column(Enum(AccountStatus), default=AccountStatus.active)
    created_at = Column(DateTime, default=datetime.utcnow)

    owner = relationship("User", back_populates="accounts")


class Transaction(Base):
    __tablename__ = "transactions"

    id = Column(UUID(as_uuid=False), primary_key=True, default=gen_uuid)
    account_id = Column(UUID(as_uuid=False), ForeignKey("accounts.id"), nullable=False)
    type = Column(Enum(TransactionType), nullable=False)
    amount = Column(Numeric(14, 2), nullable=False)
    transfer_group_id = Column(UUID(as_uuid=False), nullable=True, index=True)  # links debit+credit rows
    status = Column(Enum(TransactionStatus), default=TransactionStatus.pending)
    initiated_by = Column(UUID(as_uuid=False), ForeignKey("users.id"), nullable=False)
    exchange_rate = Column(Numeric(18, 8), nullable=True)  # set only on cross-currency transfer legs
    source = Column(String, nullable=True)  # funding source label, mainly for deposits (e.g. "BLOM Bank ••••4521")
    method = Column(String, nullable=True)  # withdrawal method: "atm" / "branch_teller" / "cash_back"
    category = Column(Enum(TransactionCategory), nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)
# ---------- Extended banking ----------

class Loan(Base):
    __tablename__ = "loans"

    id = Column(UUID(as_uuid=False), primary_key=True, default=gen_uuid)
    client_id = Column(UUID(as_uuid=False), ForeignKey("users.id"), nullable=False)
    amount = Column(Numeric(14, 2), nullable=False)
    interest_rate = Column(Numeric(5, 2), nullable=True)  # set by the bank at approval, not the client
    term_months = Column(Numeric, nullable=False)
    purpose = Column(String, nullable=True)
    disbursement_account_id = Column(UUID(as_uuid=False), ForeignKey("accounts.id"), nullable=True)
    disbursed_at = Column(DateTime, nullable=True)
    total_repayment = Column(Numeric(14, 2), nullable=True)  # principal + simple interest, set at approval
    monthly_payment = Column(Numeric(14, 2), nullable=True)
    remaining_balance = Column(Numeric(14, 2), nullable=True)
    next_payment_due = Column(DateTime, nullable=True)
    status = Column(Enum(LoanStatus), default=LoanStatus.pending)
    approved_by = Column(UUID(as_uuid=False), ForeignKey("users.id"), nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    
class Card(Base):
    __tablename__ = "cards"

    id = Column(UUID(as_uuid=False), primary_key=True, default=gen_uuid)
    account_id = Column(UUID(as_uuid=False), ForeignKey("accounts.id"), nullable=False)
    masked_number = Column(String, nullable=False)
    type = Column(Enum(CardType), nullable=False)
    tier = Column(Enum(CardTier), default=CardTier.standard)
    status = Column(Enum(CardStatus), default=CardStatus.active)
    expiry_date = Column(DateTime, nullable=False)
    activated_at = Column(DateTime, nullable=True)  # employee approval alone doesn't make a card usable - client must activate it
    frozen = Column(Boolean, default=False, nullable=False)  # instant, reversible lock - distinct from cancel (permanent)
    created_at = Column(DateTime, default=datetime.utcnow)
class Statement(Base):
    __tablename__ = "statements"

    id = Column(UUID(as_uuid=False), primary_key=True, default=gen_uuid)
    account_id = Column(UUID(as_uuid=False), ForeignKey("accounts.id"), nullable=False)
    period_start = Column(DateTime, nullable=False)
    period_end = Column(DateTime, nullable=False)
    opening_balance = Column(Numeric(14, 2), nullable=True)
    closing_balance = Column(Numeric(14, 2), nullable=True)
    total_deposits = Column(Numeric(14, 2), nullable=True)
    total_withdrawals = Column(Numeric(14, 2), nullable=True)
    currency = Column(String, nullable=True)
    transactions_snapshot = Column(JSON, nullable=True)  # frozen list of transaction lines at generation time
    generated_at = Column(DateTime, default=datetime.utcnow)

# ---------- Governance ----------

class Approval(Base):
    __tablename__ = "approvals"

    id = Column(UUID(as_uuid=False), primary_key=True, default=gen_uuid)
    entity_type = Column(Enum(ApprovalEntityType), nullable=False)
    entity_id = Column(UUID(as_uuid=False), nullable=False)
    requested_by = Column(UUID(as_uuid=False), ForeignKey("users.id"), nullable=False)
    approved_by = Column(UUID(as_uuid=False), ForeignKey("users.id"), nullable=True)
    status = Column(Enum(ApprovalStatus), default=ApprovalStatus.pending)
    notes = Column(Text, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)


class AuditLog(Base):
    __tablename__ = "audit_logs"

    id = Column(UUID(as_uuid=False), primary_key=True, default=gen_uuid)
    actor_id = Column(UUID(as_uuid=False), ForeignKey("users.id"), nullable=False)
    action = Column(String, nullable=False)
    entity_type = Column(String, nullable=False)
    entity_id = Column(UUID(as_uuid=False), nullable=False)
    details = Column(JSON, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)


# ---------- AI Agents ----------

class AgentConversation(Base):
    __tablename__ = "agent_conversations"

    id = Column(UUID(as_uuid=False), primary_key=True, default=gen_uuid)
    user_id = Column(UUID(as_uuid=False), ForeignKey("users.id"), nullable=False)
    agent_type = Column(Enum(AgentType), nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow)


class AgentMessage(Base):
    __tablename__ = "agent_messages"

    id = Column(UUID(as_uuid=False), primary_key=True, default=gen_uuid)
    conversation_id = Column(UUID(as_uuid=False), ForeignKey("agent_conversations.id"), nullable=False)
    role = Column(Enum(AgentMessageRole), nullable=False)
    content = Column(Text, nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow)


class AgentActionLog(Base):
    __tablename__ = "agent_actions_log"

    id = Column(UUID(as_uuid=False), primary_key=True, default=gen_uuid)
    conversation_id = Column(UUID(as_uuid=False), ForeignKey("agent_conversations.id"), nullable=False)
    tool_name = Column(String, nullable=False)
    input = Column(JSON, nullable=True)
    output = Column(JSON, nullable=True)
    status = Column(Enum(AgentActionStatus), default=AgentActionStatus.pending_approval)
    created_at = Column(DateTime, default=datetime.utcnow)


class EmployeeProfile(Base):
    __tablename__ = "employee_profiles"

    id = Column(UUID(as_uuid=False), primary_key=True, default=gen_uuid)
    user_id = Column(UUID(as_uuid=False), ForeignKey("users.id"), unique=True, nullable=False)
    employee_id = Column(String, unique=True, nullable=False)
    department = Column(String, nullable=False)
    branch = Column(String, nullable=False)
    job_title = Column(String, nullable=False)
    hire_date = Column(DateTime, nullable=False)
    status = Column(Enum(EmployeeStatus), default=EmployeeStatus.active)
    created_at = Column(DateTime, default=datetime.utcnow)

    user = relationship("User")


class TransferVerification(Base):
    __tablename__ = "transfer_verifications"

    id = Column(UUID(as_uuid=False), primary_key=True, default=gen_uuid)
    initiated_by = Column(UUID(as_uuid=False), ForeignKey("users.id"), nullable=False)
    from_account_id = Column(UUID(as_uuid=False), ForeignKey("accounts.id"), nullable=False)
    to_account_id = Column(UUID(as_uuid=False), ForeignKey("accounts.id"), nullable=False)
    amount = Column(Numeric(14, 2), nullable=False)
    otp = Column(String, nullable=False)
    otp_expires_at = Column(DateTime, nullable=False)
    verified = Column(Boolean, default=False, nullable=False)
    attempts = Column(Numeric, default=0, nullable=False)  # wrong-code attempts, locks after 3
    locked = Column(Boolean, default=False, nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow)


class KnowledgeDocument(Base):
    __tablename__ = "knowledge_documents"

    id = Column(UUID(as_uuid=False), primary_key=True, default=gen_uuid)
    title = Column(String, nullable=False)
    filename = Column(String, nullable=False)
    uploaded_by = Column(UUID(as_uuid=False), ForeignKey("users.id"), nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow)


class KnowledgeChunk(Base):
    __tablename__ = "knowledge_chunks"

    id = Column(UUID(as_uuid=False), primary_key=True, default=gen_uuid)
    document_id = Column(UUID(as_uuid=False), ForeignKey("knowledge_documents.id"), nullable=False)
    content = Column(Text, nullable=False)
    embedding = Column(Vector(1536), nullable=True)
    chunk_index = Column(Numeric, nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow)


class ContributionMode(str, enum.Enum):
    fixed = "fixed"
    variable = "variable"


class SavingsGoal(Base):
    __tablename__ = "savings_goals"

    id = Column(UUID(as_uuid=False), primary_key=True, default=gen_uuid)
    client_id = Column(UUID(as_uuid=False), ForeignKey("users.id"), nullable=False)
    name = Column(String, nullable=False)
    target_amount = Column(Numeric(14, 2), nullable=False)
    goal_account_id = Column(UUID(as_uuid=False), ForeignKey("accounts.id"), nullable=True)
    source_account_id = Column(UUID(as_uuid=False), ForeignKey("accounts.id"), nullable=True)
    contribution_mode = Column(Enum(ContributionMode), nullable=True)
    fixed_monthly_amount = Column(Numeric(14, 2), nullable=True)
    active = Column(Boolean, default=True, nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow)


class FraudFlagStatus(str, enum.Enum):
    pending = "pending"
    cleared = "cleared"
    confirmed_fraud = "confirmed_fraud"


class FraudFlagSeverity(str, enum.Enum):
    low = "low"
    medium = "medium"
    high = "high"


class FraudFlag(Base):
    __tablename__ = "fraud_flags"

    id = Column(UUID(as_uuid=False), primary_key=True, default=gen_uuid)
    transaction_id = Column(UUID(as_uuid=False), ForeignKey("transactions.id"), nullable=False)
    account_id = Column(UUID(as_uuid=False), ForeignKey("accounts.id"), nullable=False)
    reason = Column(Text, nullable=False)
    severity = Column(Enum(FraudFlagSeverity), nullable=False)
    status = Column(Enum(FraudFlagStatus), default=FraudFlagStatus.pending, nullable=False)
    reviewed_by = Column(UUID(as_uuid=False), ForeignKey("users.id"), nullable=True)
    notes = Column(Text, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)


class AccountOwner(Base):
    __tablename__ = "account_owners"

    id = Column(UUID(as_uuid=False), primary_key=True, default=gen_uuid)
    account_id = Column(UUID(as_uuid=False), ForeignKey("accounts.id"), nullable=False)
    user_id = Column(UUID(as_uuid=False), ForeignKey("users.id"), nullable=False)
    invited_by = Column(UUID(as_uuid=False), ForeignKey("users.id"), nullable=True)
    is_primary = Column(Boolean, default=False, nullable=False)
    status = Column(Enum(JointOwnerStatus), default=JointOwnerStatus.pending, nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow)
    responded_at = Column(DateTime, nullable=True)

class FundingSource(Base):
    """An external bank account or card a client has linked as a deposit
    source. Must go through micro-deposit verification before it can
    actually be used to deposit money."""
    __tablename__ = "funding_sources"

    id = Column(UUID(as_uuid=False), primary_key=True, default=gen_uuid)
    user_id = Column(UUID(as_uuid=False), ForeignKey("users.id"), nullable=False)
    bank_name = Column(String, nullable=False)
    masked_account_number = Column(String, nullable=False)  # e.g. "••••4521"
    status = Column(Enum(FundingSourceStatus), default=FundingSourceStatus.pending_verification, nullable=False)
    micro_deposit_1 = Column(Numeric(4, 2), nullable=True)
    micro_deposit_2 = Column(Numeric(4, 2), nullable=True)
    verification_attempts = Column(Numeric, default=0, nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow)
    verified_at = Column(DateTime, nullable=True)