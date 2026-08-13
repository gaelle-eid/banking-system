import uuid
import random
from datetime import datetime, timedelta
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from app.core.database import get_db
from app.core.deps import get_current_user
from app.core.email import send_transaction_email
from app.core.limits import check_transaction_limits, check_deposit_source_limit, check_atm_withdrawal_limit, MAX_CASH_BACK_PER_TRANSACTION, is_new_phone_recipient, check_new_recipient_transfer_limit, MAX_OTP_ATTEMPTS
from app.core.fraud_detection import check_transaction_for_fraud
from app.core.account_access import get_accessible_account_ids, user_can_access_account
from app.core.exchange_rates import convert as convert_currency
from app.models.models import Account, Transaction, TransactionType, TransactionStatus, User, TransferVerification, FundingSource, FundingSourceStatus, Card, CardType, CardStatus
from app.schemas.transaction import DepositRequest, WithdrawalRequest, TransferRequest, TransactionOut, PhoneTransferInitiateRequest, PhoneTransferInitiateOut, PhoneTransferConfirmRequest
from app.core.email import send_transfer_otp_email

router = APIRouter(prefix="/transactions", tags=["transactions"])


async def _get_owned_account(db: AsyncSession, account_id: str, user: User, allow_closed: bool = False) -> Account:
    result = await db.execute(select(Account).where(Account.id == account_id))
    account = result.scalar_one_or_none()
    if not account:
        raise HTTPException(status_code=404, detail="Account not found")
    if user.role.value == "client" and not await user_can_access_account(db, user.id, account_id):
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

    source_result = await db.execute(select(FundingSource).where(FundingSource.id == payload.funding_source_id))
    funding_source = source_result.scalar_one_or_none()
    if not funding_source or funding_source.user_id != current_user.id:
        raise HTTPException(status_code=404, detail="Funding source not found")
    if funding_source.status != FundingSourceStatus.verified:
        raise HTTPException(status_code=400, detail="This funding source hasn't been verified yet. Verify it before depositing from it.")

    try:
        await check_transaction_limits(db, account, payload.amount, is_outgoing=False)
        check_deposit_source_limit(funding_source, payload.amount)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))

    source_label = f"{funding_source.bank_name} {funding_source.masked_account_number}"

    account.balance += payload.amount
    tx = Transaction(
        account_id=account.id,
        type=TransactionType.deposit,
        amount=payload.amount,
        status=TransactionStatus.completed,
        initiated_by=current_user.id,
        source=source_label,
    )
    db.add(tx)
    await db.commit()
    await db.refresh(tx)

    try:
        send_transaction_email(
            current_user.email, current_user.full_name, "deposit",
            f"{payload.amount} {account.currency} (via {source_label})",
            account.nickname or account.type.value,
            f"{account.balance} {account.currency}",
        )
    except Exception:
        pass

    try:
        await check_transaction_for_fraud(db, account, tx, current_user)
        await db.commit()
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

    if payload.method not in ("atm", "branch_teller", "cash_back"):
        raise HTTPException(status_code=400, detail="Invalid withdrawal method")

    method_label = None
    if payload.method == "atm":
        if not payload.card_id:
            raise HTTPException(status_code=400, detail="Select a debit card for ATM withdrawal")
        card_result = await db.execute(select(Card).where(Card.id == payload.card_id))
        card = card_result.scalar_one_or_none()
        if not card or card.account_id != account.id:
            raise HTTPException(status_code=404, detail="Card not found on this account")
        if card.type != CardType.debit:
            raise HTTPException(status_code=400, detail="ATM withdrawals require a debit card")
        if card.status != CardStatus.active:
            raise HTTPException(status_code=400, detail=f"This card is {card.status.value}, not active - ATM withdrawal isn't available")
        if not card.activated_at:
            raise HTTPException(status_code=400, detail="Please activate this card before using it - go to Cards to activate it.")
        if card.frozen:
            raise HTTPException(status_code=400, detail="This card is frozen. Unfreeze it in Cards before using it.")
        method_label = f"ATM - Debit Card {card.masked_number[-9:]}"
    elif payload.method == "branch_teller":
        method_label = "Branch Teller Withdrawal"
    elif payload.method == "cash_back":
        if payload.amount > MAX_CASH_BACK_PER_TRANSACTION:
            raise HTTPException(status_code=400, detail=f"Cash back is limited to {MAX_CASH_BACK_PER_TRANSACTION} per transaction")
        method_label = "Cash Back at Checkout"

    try:
        await check_transaction_limits(db, account, payload.amount, is_outgoing=True)
        if payload.method == "atm":
            await check_atm_withdrawal_limit(db, account.id, payload.amount, card.tier.value)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))

    account.balance -= payload.amount
    tx = Transaction(
        account_id=account.id,
        type=TransactionType.withdrawal,
        amount=payload.amount,
        status=TransactionStatus.completed,
        initiated_by=current_user.id,
        method=payload.method,
        source=method_label,
    )
    db.add(tx)
    await db.commit()
    await db.refresh(tx)

    try:
        send_transaction_email(
            current_user.email, current_user.full_name, "withdrawal",
            f"{payload.amount} {account.currency} ({method_label})",
            account.nickname or account.type.value,
            f"{account.balance} {account.currency}",
        )
    except Exception:
        pass

    try:
        await check_transaction_for_fraud(db, account, tx, current_user)
        await db.commit()
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

    exchange_rate = None
    credit_amount = payload.amount
    if from_account.currency != to_account.currency:
        try:
            credit_amount, exchange_rate = await convert_currency(
                payload.amount, from_account.currency, to_account.currency
            )
        except ValueError as e:
            raise HTTPException(status_code=400, detail=str(e))
        except Exception:
            raise HTTPException(status_code=503, detail="Exchange rate service is temporarily unavailable, please try again")

    from_account.balance -= payload.amount
    to_account.balance += credit_amount

    debit_tx = Transaction(
        account_id=from_account.id,
        type=TransactionType.transfer_debit,
        amount=payload.amount,
        transfer_group_id=group_id,
        status=TransactionStatus.completed,
        initiated_by=current_user.id,
        exchange_rate=exchange_rate,
    )
    credit_tx = Transaction(
        account_id=to_account.id,
        type=TransactionType.transfer_credit,
        amount=credit_amount,
        transfer_group_id=group_id,
        status=TransactionStatus.completed,
        initiated_by=current_user.id,
        exchange_rate=exchange_rate,
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
                f"{credit_amount} {to_account.currency}",
                to_account.nickname or to_account.type.value,
                f"{to_account.balance} {to_account.currency}",
            )
    except Exception:
        pass

    try:
        await check_transaction_for_fraud(db, from_account, debit_tx, current_user)
        await db.commit()
    except Exception:
        pass

    return [debit_tx, credit_tx]


@router.get("/{account_id}", response_model=list[TransactionOut])
async def get_account_transactions(
    account_id: str,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    await _get_owned_account(db, account_id, current_user, allow_closed=True)
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
    my_account_ids = await get_accessible_account_ids(db, current_user.id)

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
        if not recipient_account or recipient_account.id in my_account_ids:
            continue

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


@router.post("/phone-transfer/initiate", response_model=PhoneTransferInitiateOut)
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
    if not recipient.phone_verified:
        raise HTTPException(status_code=400, detail=f"{recipient.full_name}'s phone number isn't verified, so transfers to it aren't available.")

    result = await db.execute(select(Account).where(Account.owner_id == recipient.id).limit(1))
    to_account = result.scalar_one_or_none()
    if not to_account:
        raise HTTPException(status_code=404, detail=f"{recipient.full_name} has no accounts to receive the transfer")

    if from_account.balance < payload.amount:
        raise HTTPException(status_code=400, detail="Insufficient funds")

    is_new = await is_new_phone_recipient(db, current_user.id, to_account.id)

    try:
        await check_transaction_limits(db, from_account, payload.amount, is_outgoing=True)
        check_new_recipient_transfer_limit(is_new, payload.amount)
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

    return PhoneTransferInitiateOut(
        verification_id=verification.id,
        recipient_name=recipient.full_name,
        message=f"Verification code sent. Confirm to send {payload.amount} {from_account.currency} to {recipient.full_name}.",
    )


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
    if verification.locked:
        raise HTTPException(status_code=400, detail="Too many incorrect attempts. Please start the transfer again.")
    if datetime.utcnow() > verification.otp_expires_at:
        raise HTTPException(status_code=400, detail="This code has expired. Please start the transfer again.")
    if payload.otp != verification.otp:
        verification.attempts = int(verification.attempts) + 1
        if int(verification.attempts) >= MAX_OTP_ATTEMPTS:
            verification.locked = True
            await db.commit()
            raise HTTPException(status_code=400, detail="Too many incorrect attempts. This transfer has been cancelled - please start again.")
        await db.commit()
        remaining = MAX_OTP_ATTEMPTS - int(verification.attempts)
        raise HTTPException(status_code=400, detail=f"Incorrect code. {remaining} attempt{'s' if remaining != 1 else ''} left.")

    from_result = await db.execute(select(Account).where(Account.id == verification.from_account_id))
    from_account = from_result.scalar_one_or_none()
    to_result = await db.execute(select(Account).where(Account.id == verification.to_account_id))
    to_account = to_result.scalar_one_or_none()

    if not from_account or not to_account:
        raise HTTPException(status_code=404, detail="Account no longer exists")
    if from_account.balance < verification.amount:
        raise HTTPException(status_code=400, detail="Insufficient funds")

    group_id = str(uuid.uuid4())

    exchange_rate = None
    credit_amount = verification.amount
    if from_account.currency != to_account.currency:
        try:
            credit_amount, exchange_rate = await convert_currency(
                verification.amount, from_account.currency, to_account.currency
            )
        except ValueError as e:
            raise HTTPException(status_code=400, detail=str(e))
        except Exception:
            raise HTTPException(status_code=503, detail="Exchange rate service is temporarily unavailable, please try again")

    from_account.balance -= verification.amount
    to_account.balance += credit_amount

    debit_tx = Transaction(
        account_id=from_account.id, type=TransactionType.transfer_debit,
        amount=verification.amount, transfer_group_id=group_id,
        status=TransactionStatus.completed, initiated_by=current_user.id,
        exchange_rate=exchange_rate,
    )
    credit_tx = Transaction(
        account_id=to_account.id, type=TransactionType.transfer_credit,
        amount=credit_amount, transfer_group_id=group_id,
        status=TransactionStatus.completed, initiated_by=current_user.id,
        exchange_rate=exchange_rate,
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

    try:
        await check_transaction_for_fraud(db, from_account, debit_tx, current_user)
        await db.commit()
    except Exception:
        pass

    return [debit_tx, credit_tx]