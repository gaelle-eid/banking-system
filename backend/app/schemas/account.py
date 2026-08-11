from pydantic import BaseModel
from decimal import Decimal
from datetime import datetime
from app.models.models import AccountType, AccountStatus, JointOwnerStatus

class AccountCreate(BaseModel):
    type: AccountType
    currency: str = "USD"
    nickname: str | None = None


class AccountOut(BaseModel):
    id: str
    owner_id: str
    account_number: str
    nickname: str | None
    type: AccountType
    balance: Decimal
    currency: str
    status: AccountStatus
    created_at: datetime
    is_joint: bool = False

    class Config:
        from_attributes = True


class JointOwnerAdd(BaseModel):
    email: str


class JointOwnerOut(BaseModel):
    user_id: str
    full_name: str
    email: str
    is_primary: bool
    status: JointOwnerStatus

    class Config:
        from_attributes = True


class JointInvitationOut(BaseModel):
    """A pending (or resolved) joint-account invitation, from the
    perspective of the person who was invited."""
    invitation_id: str
    account_id: str
    account_nickname: str | None
    account_type: AccountType
    masked_account_number: str
    invited_by_name: str
    status: JointOwnerStatus
    created_at: datetime

    class Config:
        from_attributes = True