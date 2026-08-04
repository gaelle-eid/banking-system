import uuid

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from app.core.database import get_db
from app.core.deps import get_current_user
from app.models.models import Account, Transaction, TransactionType, TransactionStatus, User
from app.schemas.transaction import DepositRequest, WithdrawalRequest, TransferRequest, TransactionOut

router = APIRouter(prefix="/transactions", tags=["transactions"])


async def _get_owned_account(db: AsyncSession, account_id: str, user: User) -> Account:
    result = await db.execute(select(Account).where(Account.id == account_id))
    account = result.scalar_one_or_none()
    if not account:
        raise HTTPException(status_code=404, detail="Account not found")
    if account.owner_id != user.id and user.role.value == "client":
        raise HTTPException(status_code=403, detail="Not your account")
    return account


@router.post("/deposit", response_model=TransactionOut, status_code=status.HTTP_201_CREATED)
async def deposit(
    payload: DepositRequest,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    account = await _get_owned_account(db, payload.account_id, current_user)

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
    return [debit_tx, credit_tx]


@router.get("/{account_id}", response_model=list[TransactionOut])
async def get_account_transactions(
    account_id: str,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    await _get_owned_account(db, account_id, current_user)  # ownership check
    result = await db.execute(
        select(Transaction).where(Transaction.account_id == account_id).order_by(Transaction.created_at.desc())
    )
    return result.scalars().all()