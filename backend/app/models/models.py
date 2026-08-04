import uuid
import enum
from datetime import datetime

from sqlalchemy import (
    Column, String, Numeric, ForeignKey, DateTime, Enum, Text, JSON
)
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


class AccountStatus(str, enum.Enum):
    active = "active"
    frozen = "frozen"
    closed = "closed"


class TransactionType(str, enum.Enum):
    deposit = "deposit"
    withdrawal = "withdrawal"
    transfer_debit = "transfer_debit"
    transfer_credit = "transfer_credit"


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


# ---------- Core ----------

class User(Base):
    __tablename__ = "users"

    id = Column(UUID(as_uuid=False), primary_key=True, default=gen_uuid)
    email = Column(String, unique=True, nullable=False, index=True)
    password_hash = Column(String, nullable=False)
    full_name = Column(String, nullable=False)
    role = Column(Enum(UserRole), nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow)

    accounts = relationship("Account", back_populates="owner")


class Account(Base):
    __tablename__ = "accounts"

    id = Column(UUID(as_uuid=False), primary_key=True, default=gen_uuid)
    owner_id = Column(UUID(as_uuid=False), ForeignKey("users.id"), nullable=False)
    account_number = Column(String, unique=True, nullable=False)
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
    created_at = Column(DateTime, default=datetime.utcnow)


# ---------- Extended banking ----------

class Loan(Base):
    __tablename__ = "loans"

    id = Column(UUID(as_uuid=False), primary_key=True, default=gen_uuid)
    client_id = Column(UUID(as_uuid=False), ForeignKey("users.id"), nullable=False)
    amount = Column(Numeric(14, 2), nullable=False)
    interest_rate = Column(Numeric(5, 2), nullable=False)
    term_months = Column(Numeric, nullable=False)
    status = Column(Enum(LoanStatus), default=LoanStatus.pending)
    approved_by = Column(UUID(as_uuid=False), ForeignKey("users.id"), nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)


class Card(Base):
    __tablename__ = "cards"

    id = Column(UUID(as_uuid=False), primary_key=True, default=gen_uuid)
    account_id = Column(UUID(as_uuid=False), ForeignKey("accounts.id"), nullable=False)
    masked_number = Column(String, nullable=False)
    type = Column(Enum(CardType), nullable=False)
    status = Column(Enum(CardStatus), default=CardStatus.active)
    expiry_date = Column(DateTime, nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow)


class Statement(Base):
    __tablename__ = "statements"

    id = Column(UUID(as_uuid=False), primary_key=True, default=gen_uuid)
    account_id = Column(UUID(as_uuid=False), ForeignKey("accounts.id"), nullable=False)
    period_start = Column(DateTime, nullable=False)
    period_end = Column(DateTime, nullable=False)
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