from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from app.core.database import get_db
from app.core.deps import require_role
from app.core.audit import log_action
from app.core.email import send_email
from app.models.models import User, UserRole, RegistrationStatus
from app.schemas.registration import PendingRegistrationOut, RegistrationDecisionRequest

router = APIRouter(prefix="/registrations", tags=["registrations"])


@router.get("/pending", response_model=list[PendingRegistrationOut], dependencies=[Depends(require_role(UserRole.employee, UserRole.admin))])
async def list_pending_registrations(db: AsyncSession = Depends(get_db)):
    result = await db.execute(
        select(User).where(
            User.role == UserRole.client,
            User.is_verified == True,
            User.registration_status == RegistrationStatus.pending_review,
        ).order_by(User.created_at.asc())
    )
    return result.scalars().all()


@router.post("/{user_id}/approve", dependencies=[Depends(require_role(UserRole.employee, UserRole.admin))])
async def approve_registration(
    user_id: str,
    payload: RegistrationDecisionRequest,
    current_user=Depends(require_role(UserRole.employee, UserRole.admin)),
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(select(User).where(User.id == user_id))
    user = result.scalar_one_or_none()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    if user.registration_status != RegistrationStatus.pending_review:
        raise HTTPException(status_code=400, detail=f"Registration is already {user.registration_status.value}")

    user.registration_status = RegistrationStatus.approved
    await log_action(db, current_user.id, "approved", "registration", user.id, details={"notes": payload.notes})
    await db.commit()

    try:
        send_email(
            user.email, "Your account has been approved",
            f"<p>Hi {user.full_name},</p><p>Good news - your account application has been approved. You can now log in and start banking.</p>",
        )
    except Exception:
        pass

    return {"status": "approved"}


@router.post("/{user_id}/reject", dependencies=[Depends(require_role(UserRole.employee, UserRole.admin))])
async def reject_registration(
    user_id: str,
    payload: RegistrationDecisionRequest,
    current_user=Depends(require_role(UserRole.employee, UserRole.admin)),
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(select(User).where(User.id == user_id))
    user = result.scalar_one_or_none()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    if user.registration_status != RegistrationStatus.pending_review:
        raise HTTPException(status_code=400, detail=f"Registration is already {user.registration_status.value}")

    user.registration_status = RegistrationStatus.rejected
    await log_action(db, current_user.id, "rejected", "registration", user.id, details={"notes": payload.notes})
    await db.commit()

    try:
        send_email(
            user.email, "Update on your account application",
            f"<p>Hi {user.full_name},</p><p>We're unable to approve your account application at this time. Please contact support if you have questions.</p>",
        )
    except Exception:
        pass

    return {"status": "rejected"}