from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from sqlalchemy.orm import selectinload

from app.core.database import get_db
from app.core.deps import require_role
from app.core.security import hash_password
from app.core.audit import log_action
from app.models.models import User, UserRole, EmployeeProfile, EmployeeStatus
from app.schemas.employee import (
    EmployeeCreateRequest, EmployeeOut, UserUpdateRequest, EmployeeStatusUpdateRequest,
)

router = APIRouter(prefix="/admin/employees", tags=["admin"])


@router.post("", response_model=EmployeeOut, status_code=201, dependencies=[Depends(require_role(UserRole.admin))])
async def create_employee(payload: EmployeeCreateRequest, db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(User).where(User.email == payload.email))
    if result.scalar_one_or_none():
        raise HTTPException(status_code=400, detail="Email already registered")

    result = await db.execute(select(EmployeeProfile).where(EmployeeProfile.employee_id == payload.employee_id))
    if result.scalar_one_or_none():
        raise HTTPException(status_code=400, detail="Employee ID already in use")

    user = User(
        email=payload.email,
        password_hash=hash_password(payload.password),
        full_name=payload.full_name,
        phone=payload.phone,
        role=UserRole.employee,
        is_verified=True,  # admin-created accounts are pre-verified, no email flow needed
    )
    db.add(user)
    await db.flush()

    profile = EmployeeProfile(
        user_id=user.id,
        employee_id=payload.employee_id,
        department=payload.department,
        branch=payload.branch,
        job_title=payload.job_title,
        hire_date=payload.hire_date,
    )
    db.add(profile)
    await db.commit()

    result = await db.execute(
        select(User).options(selectinload(User.accounts)).where(User.id == user.id)
    )
    user = result.scalar_one()
    user_out = EmployeeOut.model_validate(user)
    user_out.profile = profile
    return user_out


@router.get("", response_model=list[EmployeeOut], dependencies=[Depends(require_role(UserRole.admin))])
async def list_employees(db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(User).where(User.role == UserRole.employee))
    employees = result.scalars().all()

    output = []
    for emp in employees:
        prof_result = await db.execute(select(EmployeeProfile).where(EmployeeProfile.user_id == emp.id))
        profile = prof_result.scalar_one_or_none()
        emp_out = EmployeeOut.model_validate(emp)
        emp_out.profile = profile
        output.append(emp_out)
    return output


@router.patch("/{user_id}/status", response_model=EmployeeOut, dependencies=[Depends(require_role(UserRole.admin))])
async def update_employee_status(user_id: str, payload: EmployeeStatusUpdateRequest, db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(EmployeeProfile).where(EmployeeProfile.user_id == user_id))
    profile = result.scalar_one_or_none()
    if not profile:
        raise HTTPException(status_code=404, detail="Employee profile not found")

    profile.status = payload.status
    await db.commit()

    result = await db.execute(select(User).where(User.id == user_id))
    user = result.scalar_one()
    emp_out = EmployeeOut.model_validate(user)
    emp_out.profile = profile
    return emp_out