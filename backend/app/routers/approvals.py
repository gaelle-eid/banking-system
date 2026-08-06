from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from app.core.database import get_db
from app.core.deps import get_current_user, require_role
from app.core.audit import log_action
from app.models.models import (
    Approval, ApprovalStatus, ApprovalEntityType,
    Loan, LoanStatus, Card, CardStatus,
    User, UserRole,
)
from app.schemas.approval import ApprovalOut, ApprovalActionRequest

router = APIRouter(prefix="/approvals", tags=["approvals"])


@router.get("", response_model=list[ApprovalOut], dependencies=[Depends(require_role(UserRole.employee, UserRole.admin))])
async def list_approvals(
    status: ApprovalStatus | None = Query(None),
    entity_type: ApprovalEntityType | None = Query(None),
    db: AsyncSession = Depends(get_db),
):
    query = select(Approval)
    if status:
        query = query.where(Approval.status == status)
    if entity_type:
        query = query.where(Approval.entity_type == entity_type)
    query = query.order_by(Approval.created_at.desc())

    result = await db.execute(query)
    return result.scalars().all()


@router.post("/{approval_id}/approve", response_model=ApprovalOut, dependencies=[Depends(require_role(UserRole.employee, UserRole.admin))])
async def approve_request(
    approval_id: str,
    payload: ApprovalActionRequest,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(select(Approval).where(Approval.id == approval_id))
    approval = result.scalar_one_or_none()
    if not approval:
        raise HTTPException(status_code=404, detail="Approval not found")
    if approval.status != ApprovalStatus.pending:
        raise HTTPException(status_code=400, detail=f"Approval is already {approval.status.value}")

    if approval.entity_type == ApprovalEntityType.loan:
        loan_result = await db.execute(select(Loan).where(Loan.id == approval.entity_id))
        loan = loan_result.scalar_one_or_none()
        if loan:
            loan.status = LoanStatus.active
            loan.approved_by = current_user.id

    elif approval.entity_type == ApprovalEntityType.card:
        card_result = await db.execute(select(Card).where(Card.id == approval.entity_id))
        card = card_result.scalar_one_or_none()
        if card:
            card.status = CardStatus.active

    approval.status = ApprovalStatus.approved
    approval.approved_by = current_user.id
    approval.notes = payload.notes

    await log_action(
        db, current_user.id, "approve", approval.entity_type.value, approval.entity_id,
        details={"approval_id": approval.id, "notes": payload.notes},
    )

    await db.commit()
    await db.refresh(approval)
    return approval


@router.post("/{approval_id}/reject", response_model=ApprovalOut, dependencies=[Depends(require_role(UserRole.employee, UserRole.admin))])
async def reject_request(
    approval_id: str,
    payload: ApprovalActionRequest,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(select(Approval).where(Approval.id == approval_id))
    approval = result.scalar_one_or_none()
    if not approval:
        raise HTTPException(status_code=404, detail="Approval not found")
    if approval.status != ApprovalStatus.pending:
        raise HTTPException(status_code=400, detail=f"Approval is already {approval.status.value}")

    if approval.entity_type == ApprovalEntityType.loan:
        loan_result = await db.execute(select(Loan).where(Loan.id == approval.entity_id))
        loan = loan_result.scalar_one_or_none()
        if loan:
            loan.status = LoanStatus.rejected

    elif approval.entity_type == ApprovalEntityType.card:
        card_result = await db.execute(select(Card).where(Card.id == approval.entity_id))
        card = card_result.scalar_one_or_none()
        if card:
            card.status = CardStatus.blocked

    approval.status = ApprovalStatus.rejected
    approval.approved_by = current_user.id
    approval.notes = payload.notes

    await log_action(
        db, current_user.id, "reject", approval.entity_type.value, approval.entity_id,
        details={"approval_id": approval.id, "notes": payload.notes},
    )

    await db.commit()
    await db.refresh(approval)
    return approval