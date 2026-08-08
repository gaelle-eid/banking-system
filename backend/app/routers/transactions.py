import uuid
import random
from datetime import datetime, timedelta
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from app.core.database import get_db
from app.core.deps import get_current_user
from app.core.email import send_transaction_email
from app.core.limits import check_transaction_limits
from app.models.models import Account, Transaction, TransactionType, TransactionStatus, User, TransferVerification
from app.schemas.transaction import DepositRequest, WithdrawalRequest, TransferRequest, TransactionOut, PhoneTransferInitiateRequest, PhoneTransferConfirmRequest
from app.core.email import send_transfer_otp_email
router = APIRouter(prefix="/transactions", tags=["transactions"])


async def _get_owned_account(db: AsyncSession, account_id: str, user: User, allow_closed: bool = False) -> Account:
    result = await db.execute(select(Account).where(Account.id == account_id))
    account = result.scalar_one_or_none()
    if not account:
        raise HTTPException(status_code=404, detail="Account not found")
    if account.owner_id != user.id and user.role.value == "client":
        raise HTTPException(status_code=403, detail="Not your account")
    if account.status.value == "closed" and not allow_closed:
        raise HTTPException(status_code=400, detail="This account is closed")
    return account


@router.post("/deposit", response_model=TransactionOut, status_code=status.HTTP_201_CREATED)
async def deposit(
    payload: DepositRequest,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    account = await _get_owned_account(db, payload.account_id, current_user)

    try:
        await check_transaction_limits(db, account, payload.amount, is_outgoing=False)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))

    account.balance += payload.amount
    tx = Transaction(
        account_id=account.id,
        type=TransactionType.deposit,
        amount=payload.amount,
        status=TransactionStatus.completed,
        initiated_by=current_user.id,
    )
    db.add(tx)
    await db.commit()
    await db.refresh(tx)

    try:
        send_transaction_email(
            current_user.email, current_user.full_name, "deposit",
            f"{payload.amount} {account.currency}",
            account.nickname or account.type.value,
            f"{account.balance} {account.currency}",
        )
    except Exception:
        pass

    return tx


@router.post("/withdraw", response_model=TransactionOut, status_code=status.HTTP_201_CREATED)
async def withdraw(
    payload: WithdrawalRequest,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    account = await _get_owned_account(db, payload.account_id, current_user)

    if account.balance < payload.amount:
        raise HTTPException(status_code=400, detail="Insufficient funds")

    try:
        await check_transaction_limits(db, account, payload.amount, is_outgoing=True)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))

    account.balance -= payload.amount
    tx = Transaction(
        account_id=account.id,
        type=TransactionType.withdrawal,
        amount=payload.amount,
        status=TransactionStatus.completed,
        initiated_by=current_user.id,
    )
    db.add(tx)
    await db.commit()
    await db.refresh(tx)

    try:
        send_transaction_email(
            current_user.email, current_user.full_name, "withdrawal",
            f"{payload.amount} {account.currency}",
            account.nickname or account.type.value,
            f"{account.balance} {account.currency}",
        )
    except Exception:
        pass

    return tx


@router.post("/transfer", response_model=list[TransactionOut], status_code=status.HTTP_201_CREATED)
async def transfer(
    payload: TransferRequest,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    if payload.from_account_id == payload.to_account_id:
        raise HTTPException(status_code=400, detail="Cannot transfer to the same account")

    from_account = await _get_owned_account(db, payload.from_account_id, current_user)

    to_result = await db.execute(select(Account).where(Account.id == payload.to_account_id))
    to_account = to_result.scalar_one_or_none()
    if not to_account:
        raise HTTPException(status_code=404, detail="Destination account not found")

    if from_account.balance < payload.amount:
        raise HTTPException(status_code=400, detail="Insufficient funds")

    try:
        await check_transaction_limits(db, from_account, payload.amount, is_outgoing=True)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))

    group_id = str(uuid.uuid4())

    from_account.balance -= payload.amount
    to_account.balance += payload.amount

    debit_tx = Transaction(
        account_id=from_account.id,
        type=TransactionType.transfer_debit,
        amount=payload.amount,
        transfer_group_id=group_id,
        status=TransactionStatus.completed,
        initiated_by=current_user.id,
    )
    credit_tx = Transaction(
        account_id=to_account.id,
        type=TransactionType.transfer_credit,
        amount=payload.amount,
        transfer_group_id=group_id,
        status=TransactionStatus.completed,
        initiated_by=current_user.id,
    )
    db.add_all([debit_tx, credit_tx])
    await db.commit()
    await db.refresh(debit_tx)
    await db.refresh(credit_tx)

    to_owner_result = await db.execute(select(User).where(User.id == to_account.owner_id))
    to_owner = to_owner_result.scalar_one_or_none()

    try:
        send_transaction_email(
            current_user.email, current_user.full_name, "transfer_debit",
            f"{payload.amount} {from_account.currency}",
            from_account.nickname or from_account.type.value,
            f"{from_account.balance} {from_account.currency}",
        )
        if to_owner:
            send_transaction_email(
                to_owner.email, to_owner.full_name, "transfer_credit",
                f"{payload.amount} {to_account.currency}",
                to_account.nickname or to_account.type.value,
                f"{to_account.balance} {to_account.currency}",
            )
    except Exception:
        pass

    return [debit_tx, credit_tx]


@router.get("/{account_id}", response_model=list[TransactionOut])
async def get_account_transactions(
    account_id: str,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    await _get_owned_account(db, account_id, current_user, allow_closed=True)  # viewing history is fine even if closed
    result = await db.execute(
        select(Transaction).where(Transaction.account_id == account_id).order_by(Transaction.created_at.desc())
    )
    return result.scalars().all()



@router.get("/recipients/recent")
async def get_recent_recipients(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Returns people this client has sent money to before, most recent first."""
    my_accounts_result = await db.execute(select(Account).where(Account.owner_id == current_user.id))
    my_account_ids = [a.id for a in my_accounts_result.scalars().all()]

    if not my_account_ids:
        return []

    debit_result = await db.execute(
        select(Transaction)
        .where(
            Transaction.account_id.in_(my_account_ids),
            Transaction.type == TransactionType.transfer_debit,
            Transaction.transfer_group_id.isnot(None),
        )
        .order_by(Transaction.created_at.desc())
    )
    my_debits = debit_result.scalars().all()

    seen_users = {}
    for debit in my_debits:
        credit_result = await db.execute(
            select(Transaction).where(
                Transaction.transfer_group_id == debit.transfer_group_id,
                Transaction.type == TransactionType.transfer_credit,
            )
        )
        credit = credit_result.scalar_one_or_none()
        if not credit:
            continue

        account_result = await db.execute(select(Account).where(Account.id == credit.account_id))
        recipient_account = account_result.scalar_one_or_none()
        if not recipient_account or recipient_account.owner_id == current_user.id:
            continue  # skip transfers to your own other accounts

        user_result = await db.execute(select(User).where(User.id == recipient_account.owner_id))
        recipient_user = user_result.scalar_one_or_none()
        if not recipient_user:
            continue

        if recipient_user.id not in seen_users:
            seen_users[recipient_user.id] = {
                "user_id": recipient_user.id,
                "full_name": recipient_user.full_name,
                "email": recipient_user.email,
                "last_transferred_at": debit.created_at.isoformat(),
            }

    return list(seen_users.values())[:10]


@router.post("/phone-transfer/initiate")
async def initiate_phone_transfer(
    payload: PhoneTransferInitiateRequest,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    from_account = await _get_owned_account(db, payload.from_account_id, current_user)

    result = await db.execute(select(User).where(User.phone == payload.to_phone))
    recipient = result.scalar_one_or_none()
    if not recipient:
        raise HTTPException(status_code=404, detail="No client found with that phone number")

    result = await db.execute(select(Account).where(Account.owner_id == recipient.id).limit(1))
    to_account = result.scalar_one_or_none()
    if not to_account:
        raise HTTPException(status_code=404, detail=f"{recipient.full_name} has no accounts to receive the transfer")

    if from_account.balance < payload.amount:
        raise HTTPException(status_code=400, detail="Insufficient funds")

    try:
        await check_transaction_limits(db, from_account, payload.amount, is_outgoing=True)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))

    otp = f"{random.randint(0, 999999):06d}"
    verification = TransferVerification(
        initiated_by=current_user.id,
        from_account_id=from_account.id,
        to_account_id=to_account.id,
        amount=payload.amount,
        otp=otp,
        otp_expires_at=datetime.utcnow() + timedelta(minutes=5),
    )
    db.add(verification)
    await db.commit()
    await db.refresh(verification)

    try:
        send_transfer_otp_email(current_user.email, current_user.full_name, otp, f"{payload.amount} {from_account.currency}", recipient.full_name)
    except Exception:
        pass

    return {"verification_id": verification.id, "message": f"Verification code sent. Confirm to send {payload.amount} to {recipient.full_name}."}


@router.post("/phone-transfer/confirm", response_model=list[TransactionOut])
async def confirm_phone_transfer(
    payload: PhoneTransferConfirmRequest,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(select(TransferVerification).where(TransferVerification.id == payload.verification_id))
    verification = result.scalar_one_or_none()
    if not verification:
        raise HTTPException(status_code=404, detail="Verification not found")
    if verification.initiated_by != current_user.id:
        raise HTTPException(status_code=403, detail="Not your transfer")
    if verification.verified:
        raise HTTPException(status_code=400, detail="This transfer was already completed")
    if datetime.utcnow() > verification.otp_expires_at:
        raise HTTPException(status_code=400, detail="This code has expired. Please start the transfer again.")
    if payload.otp != verification.otp:
        raise HTTPException(status_code=400, detail="Incorrect code")

    from_result = await db.execute(select(Account).where(Account.id == verification.from_account_id))
    from_account = from_result.scalar_one_or_none()
    to_result = await db.execute(select(Account).where(Account.id == verification.to_account_id))
    to_account = to_result.scalar_one_or_none()

    if not from_account or not to_account:
        raise HTTPException(status_code=404, detail="Account no longer exists")
    if from_account.balance < verification.amount:
        raise HTTPException(status_code=400, detail="Insufficient funds")

    group_id = str(uuid.uuid4())
    from_account.balance -= verification.amount
    to_account.balance += verification.amount

    debit_tx = Transaction(
        account_id=from_account.id, type=TransactionType.transfer_debit,
        amount=verification.amount, transfer_group_id=group_id,
        status=TransactionStatus.completed, initiated_by=current_user.id,
    )
    credit_tx = Transaction(
        account_id=to_account.id, type=TransactionType.transfer_credit,
        amount=verification.amount, transfer_group_id=group_id,
        status=TransactionStatus.completed, initiated_by=current_user.id,
    )
    db.add_all([debit_tx, credit_tx])

    verification.verified = True

    await db.commit()
    await db.refresh(debit_tx)
    await db.refresh(credit_tx)

    try:
        send_transaction_email(
            current_user.email, current_user.full_name, "transfer_debit",
            f"{verification.amount} {from_account.currency}",
            from_account.nickname or from_account.type.value,
            f"{from_account.balance} {from_account.currency}",
        )
    except Exception:
        pass

    return [debit_tx, credit_tx]