import random
from datetime import datetime
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from app.core.database import get_db
from app.core.deps import get_current_user
from app.core.audit import log_action
from app.core.account_access import get_accessible_accounts, user_can_access_account
from app.core.email import send_transaction_email, send_joint_invitation_email
from app.core.exchange_rates import get_supported_rates, convert as convert_currency
from app.models.models import Account, AccountOwner, AccountStatus, JointOwnerStatus, User
from app.schemas.account import (
    AccountCreate, AccountOut, JointOwnerAdd, JointOwnerOut, JointInvitationOut,
    ExchangeRatesOut, ConversionPreviewOut,
)

router = APIRouter(prefix="/accounts", tags=["accounts"])


def generate_account_number() -> str:
    return "".join(str(random.randint(0, 9)) for _ in range(10))


def mask_account_number(account_number: str) -> str:
    return f"••••{account_number[-4:]}"


async def _attach_is_joint(db: AsyncSession, accounts: list[Account]) -> list[Account]:
    """Mark each account with whether it has any ACCEPTED joint owners,
    without triggering a query per account. Pending invitations don't
    count - the account isn't "joint" from anyone's perspective until
    someone has actually accepted."""
    if not accounts:
        return accounts
    account_ids = [a.id for a in accounts]
    result = await db.execute(
        select(AccountOwner.account_id).where(
            AccountOwner.account_id.in_(account_ids),
            AccountOwner.status == JointOwnerStatus.accepted,
        )
    )
    joint_ids = set(result.scalars().all())
    for acc in accounts:
        acc.is_joint = acc.id in joint_ids
    return accounts


@router.get("/exchange-rates", response_model=ExchangeRatesOut)
async def get_exchange_rates(
    current_user: User = Depends(get_current_user),
):
    """Current live exchange rates (USD-based) for all currencies this
    app supports. Used by the frontend to show conversion previews."""
    try:
        rates = await get_supported_rates()
    except Exception:
        raise HTTPException(status_code=503, detail="Exchange rate service is temporarily unavailable")
    return ExchangeRatesOut(base="USD", rates=rates)


@router.get("/convert-preview", response_model=ConversionPreviewOut)
async def get_conversion_preview(
    amount: float,
    from_currency: str,
    to_currency: str,
    current_user: User = Depends(get_current_user),
):
    """Preview what an amount converts to between two currencies, without
    executing any transfer. Used for live previews on the transfer form."""
    from decimal import Decimal
    try:
        converted, rate = await convert_currency(Decimal(str(amount)), from_currency, to_currency)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception:
        raise HTTPException(status_code=503, detail="Exchange rate service is temporarily unavailable")
    return ConversionPreviewOut(
        from_currency=from_currency, to_currency=to_currency,
        amount=Decimal(str(amount)), converted_amount=converted, rate=rate,
    )


@router.post("", response_model=AccountOut, status_code=status.HTTP_201_CREATED)
async def create_account(
    payload: AccountCreate,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    nickname = payload.nickname
    if not nickname:
        result = await db.execute(
            select(Account).where(
                Account.owner_id == current_user.id,
                Account.type == payload.type,
            )
        )
        existing_count = len(result.scalars().all())
        type_label = payload.type.value.capitalize()
        nickname = f"{type_label} {existing_count + 1}"

    account = Account(
        owner_id=current_user.id,
        account_number=generate_account_number(),
        nickname=nickname,
        type=payload.type,
        currency=payload.currency,
        balance=0,
    )
    db.add(account)
    await db.commit()
    await db.refresh(account)
    account.is_joint = False
    return account


@router.get("/me", response_model=list[AccountOut])
async def list_my_accounts(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    accounts = await get_accessible_accounts(db, current_user.id)
    return await _attach_is_joint(db, accounts)


@router.get("/{account_id}", response_model=AccountOut)
async def get_account(
    account_id: str,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(select(Account).where(Account.id == account_id))
    account = result.scalar_one_or_none()
    if not account:
        raise HTTPException(status_code=404, detail="Account not found")
    if current_user.role.value == "client" and not await user_can_access_account(db, current_user.id, account_id):
        raise HTTPException(status_code=403, detail="Not your account")
    await _attach_is_joint(db, [account])
    return account


@router.patch("/{account_id}/close", response_model=AccountOut)
async def close_account(
    account_id: str,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    from app.models.models import Card, CardStatus

    result = await db.execute(select(Account).where(Account.id == account_id))
    account = result.scalar_one_or_none()
    if not account:
        raise HTTPException(status_code=404, detail="Account not found")
    # Closing stays primary-owner-only, even for joint accounts.
    if account.owner_id != current_user.id and current_user.role.value == "client":
        raise HTTPException(status_code=403, detail="Not your account")

    if account.balance != 0:
        raise HTTPException(status_code=400, detail="Account must have a zero balance before closing")

    card_result = await db.execute(
        select(Card).where(Card.account_id == account.id, Card.status == CardStatus.active)
    )
    active_card = card_result.scalar_one_or_none()
    if active_card:
        raise HTTPException(
            status_code=400,
            detail="This account has an active card linked to it. Please cancel the card before closing the account.",
        )

    account.status = AccountStatus.closed
    await log_action(
        db, current_user.id, "closed", "account", account.id,
        details={"account_number": account.account_number, "nickname": account.nickname},
    )
    await db.commit()
    await db.refresh(account)
    account.is_joint = False
    return account


@router.get("/{account_id}/joint-owners", response_model=list[JointOwnerOut])
async def list_joint_owners(
    account_id: str,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Lists everyone invited to this account, regardless of whether they've
    accepted yet - so the primary owner can see pending invites too."""
    result = await db.execute(select(Account).where(Account.id == account_id))
    account = result.scalar_one_or_none()
    if not account:
        raise HTTPException(status_code=404, detail="Account not found")
    if current_user.role.value == "client" and not await user_can_access_account(db, current_user.id, account_id):
        raise HTTPException(status_code=403, detail="Not your account")

    owner_result = await db.execute(
        select(AccountOwner, User).join(User, User.id == AccountOwner.user_id).where(
            AccountOwner.account_id == account_id,
            AccountOwner.status != JointOwnerStatus.declined,
        )
    )
    rows = owner_result.all()
    return [
        JointOwnerOut(user_id=u.id, full_name=u.full_name, email=u.email, is_primary=ao.is_primary, status=ao.status)
        for ao, u in rows
    ]


@router.post("/{account_id}/joint-owners", response_model=JointOwnerOut, status_code=status.HTTP_201_CREATED)
async def invite_joint_owner(
    account_id: str,
    payload: JointOwnerAdd,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Invite someone to become a joint owner on an account. Only the
    primary owner (or an employee/admin) can do this. The invited person
    gets NO account access until they accept - this just creates a pending
    invitation."""
    result = await db.execute(select(Account).where(Account.id == account_id))
    account = result.scalar_one_or_none()
    if not account:
        raise HTTPException(status_code=404, detail="Account not found")
    if account.owner_id != current_user.id and current_user.role.value == "client":
        raise HTTPException(status_code=403, detail="Only the primary owner can invite joint owners")

    recipient_result = await db.execute(select(User).where(User.email == payload.email))
    recipient = recipient_result.scalar_one_or_none()
    if not recipient:
        raise HTTPException(status_code=404, detail="No client found with that email")
    if recipient.id == account.owner_id:
        raise HTTPException(status_code=400, detail="This user already owns the account")

    existing_result = await db.execute(
        select(AccountOwner).where(
            AccountOwner.account_id == account_id,
            AccountOwner.user_id == recipient.id,
            AccountOwner.status.in_([JointOwnerStatus.pending, JointOwnerStatus.accepted]),
        )
    )
    if existing_result.scalar_one_or_none():
        raise HTTPException(status_code=400, detail="This user is already a joint owner or has a pending invite on this account")

    invitation = AccountOwner(
        account_id=account_id,
        user_id=recipient.id,
        invited_by=current_user.id,
        is_primary=False,
        status=JointOwnerStatus.pending,
    )
    db.add(invitation)
    await log_action(
        db, current_user.id, "invited_joint_owner", "account", account.id,
        details={"account_number": account.account_number, "invited_email": recipient.email},
    )
    await db.commit()

    try:
        send_joint_invitation_email(
            recipient.email, recipient.full_name, current_user.full_name,
            account.nickname or account.type.value,
        )
    except Exception:
        pass

    return JointOwnerOut(
        user_id=recipient.id, full_name=recipient.full_name, email=recipient.email,
        is_primary=False, status=JointOwnerStatus.pending,
    )


@router.delete("/{account_id}/joint-owners/{user_id}", status_code=status.HTTP_204_NO_CONTENT)
async def remove_joint_owner(
    account_id: str,
    user_id: str,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Remove a joint owner (or rescind a pending invite) from an account.
    Only the primary owner (or an employee/admin) can do this."""
    result = await db.execute(select(Account).where(Account.id == account_id))
    account = result.scalar_one_or_none()
    if not account:
        raise HTTPException(status_code=404, detail="Account not found")
    if account.owner_id != current_user.id and current_user.role.value == "client":
        raise HTTPException(status_code=403, detail="Only the primary owner can remove joint owners")

    owner_result = await db.execute(
        select(AccountOwner).where(
            AccountOwner.account_id == account_id,
            AccountOwner.user_id == user_id,
            AccountOwner.status.in_([JointOwnerStatus.pending, JointOwnerStatus.accepted]),
        )
    )
    joint_owner = owner_result.scalar_one_or_none()
    if not joint_owner:
        raise HTTPException(status_code=404, detail="This user is not a joint owner on this account")

    await db.delete(joint_owner)
    await log_action(
        db, current_user.id, "removed_joint_owner", "account", account.id,
        details={"account_number": account.account_number, "removed_user_id": user_id},
    )
    await db.commit()
    return None


@router.get("/joint-invitations/pending", response_model=list[JointInvitationOut])
async def list_pending_invitations(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Lists joint-account invitations sent TO the current user that are
    still awaiting a response."""
    result = await db.execute(
        select(AccountOwner, Account, User)
        .join(Account, Account.id == AccountOwner.account_id)
        .outerjoin(User, User.id == AccountOwner.invited_by)
        .where(
            AccountOwner.user_id == current_user.id,
            AccountOwner.status == JointOwnerStatus.pending,
        )
        .order_by(AccountOwner.created_at.desc())
    )
    rows = result.all()
    return [
        JointInvitationOut(
            invitation_id=ao.id,
            account_id=acc.id,
            account_nickname=acc.nickname,
            account_type=acc.type,
            masked_account_number=mask_account_number(acc.account_number),
            invited_by_name=inviter.full_name if inviter else "A bank client",
            status=ao.status,
            created_at=ao.created_at,
        )
        for ao, acc, inviter in rows
    ]


@router.post("/joint-invitations/{invitation_id}/accept", response_model=JointInvitationOut)
async def accept_joint_invitation(
    invitation_id: str,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(select(AccountOwner).where(AccountOwner.id == invitation_id))
    invitation = result.scalar_one_or_none()
    if not invitation:
        raise HTTPException(status_code=404, detail="Invitation not found")
    if invitation.user_id != current_user.id:
        raise HTTPException(status_code=403, detail="This invitation isn't yours to respond to")
    if invitation.status != JointOwnerStatus.pending:
        raise HTTPException(status_code=400, detail="This invitation has already been responded to")

    invitation.status = JointOwnerStatus.accepted
    invitation.responded_at = datetime.utcnow()

    acc_result = await db.execute(select(Account).where(Account.id == invitation.account_id))
    account = acc_result.scalar_one_or_none()
    inviter_result = await db.execute(select(User).where(User.id == invitation.invited_by))
    inviter = inviter_result.scalar_one_or_none()

    await log_action(
        db, current_user.id, "accepted_joint_owner_invite", "account", invitation.account_id,
        details={"account_number": account.account_number if account else None},
    )
    await db.commit()

    return JointInvitationOut(
        invitation_id=invitation.id,
        account_id=account.id,
        account_nickname=account.nickname,
        account_type=account.type,
        masked_account_number=mask_account_number(account.account_number),
        invited_by_name=inviter.full_name if inviter else "A bank client",
        status=invitation.status,
        created_at=invitation.created_at,
    )


@router.post("/joint-invitations/{invitation_id}/decline", response_model=JointInvitationOut)
async def decline_joint_invitation(
    invitation_id: str,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(select(AccountOwner).where(AccountOwner.id == invitation_id))
    invitation = result.scalar_one_or_none()
    if not invitation:
        raise HTTPException(status_code=404, detail="Invitation not found")
    if invitation.user_id != current_user.id:
        raise HTTPException(status_code=403, detail="This invitation isn't yours to respond to")
    if invitation.status != JointOwnerStatus.pending:
        raise HTTPException(status_code=400, detail="This invitation has already been responded to")

    invitation.status = JointOwnerStatus.declined
    invitation.responded_at = datetime.utcnow()

    acc_result = await db.execute(select(Account).where(Account.id == invitation.account_id))
    account = acc_result.scalar_one_or_none()
    inviter_result = await db.execute(select(User).where(User.id == invitation.invited_by))
    inviter = inviter_result.scalar_one_or_none()

    await log_action(
        db, current_user.id, "declined_joint_owner_invite", "account", invitation.account_id,
        details={"account_number": account.account_number if account else None},
    )
    await db.commit()

    return JointInvitationOut(
        invitation_id=invitation.id,
        account_id=account.id,
        account_nickname=account.nickname,
        account_type=account.type,
        masked_account_number=mask_account_number(account.account_number),
        invited_by_name=inviter.full_name if inviter else "A bank client",
        status=invitation.status,
        created_at=invitation.created_at,
    )