from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from app.core.database import get_db
from app.core.deps import get_current_user, require_role
from app.core.audit import log_action
from app.core.email import send_email
from app.models.models import FraudFlag, FraudFlagStatus, Account, AccountStatus, Transaction, User, UserRole
from app.schemas.fraud import FraudFlagOut, FraudDecisionRequest

router = APIRouter(prefix="/fraud", tags=["fraud"])


@router.get("", response_model=list[FraudFlagOut], dependencies=[Depends(require_role(UserRole.employee, UserRole.admin))])
async def list_fraud_flags(
    status: FraudFlagStatus | None = Query(None),
    db: AsyncSession = Depends(get_db),
):
    query = select(FraudFlag)
    if status:
        query = query.where(FraudFlag.status == status)
    query = query.order_by(FraudFlag.created_at.desc())

    result = await db.execute(query)
    flags = result.scalars().all()

    enriched = []
    for flag in flags:
        account_result = await db.execute(select(Account).where(Account.id == flag.account_id))
        account = account_result.scalar_one_or_none()

        client_name = None
        client_email = None
        account_label = None
        if account:
            masked = f"••••{account.account_number[-4:]}"
            account_label = f"{account.nickname or account.type.value} {masked}"
            owner_result = await db.execute(select(User).where(User.id == account.owner_id))
            owner = owner_result.scalar_one_or_none()
            if owner:
                client_name = owner.full_name
                client_email = owner.email

        transaction_details = None
        tx_result = await db.execute(select(Transaction).where(Transaction.id == flag.transaction_id))
        tx = tx_result.scalar_one_or_none()
        if tx:
            transaction_details = {
                "amount": str(tx.amount),
                "currency": account.currency if account else "USD",
                "type": tx.type.value,
                "created_at": tx.created_at.isoformat(),
                "source": tx.source,
                "method": tx.method,
            }

        # Recent activity on this same account, for pattern context - was
        # this an isolated blip or part of a broader unusual streak?
        recent_transactions = []
        recent_result = await db.execute(
            select(Transaction)
            .where(Transaction.account_id == flag.account_id, Transaction.id != flag.transaction_id)
            .order_by(Transaction.created_at.desc())
            .limit(5)
        )
        for rtx in recent_result.scalars().all():
            recent_transactions.append({
                "amount": str(rtx.amount),
                "type": rtx.type.value,
                "created_at": rtx.created_at.isoformat(),
                "source": rtx.source,
            })

        # Other pending flags tied to the SAME client (across any of their
        # accounts) - lightweight case linking without a separate case model.
        related_pending_flags = []
        if account:
            client_account_ids_result = await db.execute(select(Account.id).where(Account.owner_id == account.owner_id))
            client_account_ids = [row[0] for row in client_account_ids_result.all()]
            related_result = await db.execute(
                select(FraudFlag).where(
                    FraudFlag.account_id.in_(client_account_ids),
                    FraudFlag.id != flag.id,
                    FraudFlag.status == FraudFlagStatus.pending,
                )
            )
            for rf in related_result.scalars().all():
                related_pending_flags.append({
                    "id": rf.id,
                    "reason": rf.reason,
                    "severity": rf.severity.value,
                    "created_at": rf.created_at.isoformat(),
                })

        flag_out = FraudFlagOut.model_validate(flag)
        flag_out.client_name = client_name
        flag_out.client_email = client_email
        flag_out.account_label = account_label
        flag_out.transaction_details = transaction_details
        flag_out.recent_transactions = recent_transactions
        flag_out.related_pending_flags = related_pending_flags
        enriched.append(flag_out)

    return enriched


@router.post("/{flag_id}/clear", response_model=FraudFlagOut, dependencies=[Depends(require_role(UserRole.employee, UserRole.admin))])
async def clear_fraud_flag(
    flag_id: str,
    payload: FraudDecisionRequest,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(select(FraudFlag).where(FraudFlag.id == flag_id))
    flag = result.scalar_one_or_none()
    if not flag:
        raise HTTPException(status_code=404, detail="Flag not found")
    if flag.status != FraudFlagStatus.pending:
        raise HTTPException(status_code=400, detail=f"Flag is already {flag.status.value}")

    flag.status = FraudFlagStatus.cleared
    flag.reviewed_by = current_user.id
    flag.notes = payload.notes

    await log_action(db, current_user.id, "cleared", "fraud_flag", flag.id, details={"notes": payload.notes})
    await db.commit()
    await db.refresh(flag)
    return flag


@router.post("/{flag_id}/confirm-fraud", response_model=FraudFlagOut, dependencies=[Depends(require_role(UserRole.employee, UserRole.admin))])
async def confirm_fraud(
    flag_id: str,
    payload: FraudDecisionRequest,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(select(FraudFlag).where(FraudFlag.id == flag_id))
    flag = result.scalar_one_or_none()
    if not flag:
        raise HTTPException(status_code=404, detail="Flag not found")
    if flag.status != FraudFlagStatus.pending:
        raise HTTPException(status_code=400, detail=f"Flag is already {flag.status.value}")

    flag.status = FraudFlagStatus.confirmed_fraud
    flag.reviewed_by = current_user.id
    flag.notes = payload.notes

    account_result = await db.execute(select(Account).where(Account.id == flag.account_id))
    account = account_result.scalar_one_or_none()
    if account:
        account.status = AccountStatus.frozen

        owner_result = await db.execute(select(User).where(User.id == account.owner_id))
        owner = owner_result.scalar_one_or_none()
        if owner:
            try:
                send_email(
                    owner.email, "Your account has been frozen - suspected fraud",
                    f"<p>Hi {owner.full_name},</p>"
                    f"<p>We've frozen your {account.nickname or account.type.value} account "
                    f"(ending {account.account_number[-4:]}) after confirming suspicious activity on it.</p>"
                    f"<p>No further transactions can be made on this account until it's reviewed. "
                    f"Please contact support as soon as possible to verify your identity and resolve this.</p>"
                    f"<p>If you believe this is a mistake, our support team can help sort it out.</p>",
                )
            except Exception:
                pass

    await log_action(db, current_user.id, "confirmed_fraud", "fraud_flag", flag.id, details={"notes": payload.notes, "account_frozen": True})
    await db.commit()
    await db.refresh(flag)
    return flag