from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from app.core.database import get_db
from app.core.deps import require_role
from app.models.models import User, UserRole
from app.schemas.auth import UserOut
from app.schemas.employee import UserUpdateRequest

router = APIRouter(prefix="/admin/users", tags=["admin"])


@router.get("", response_model=list[UserOut], dependencies=[Depends(require_role(UserRole.admin))])
async def list_users(db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(User).order_by(User.created_at.desc()))
    return result.scalars().all()


@router.patch("/{user_id}", response_model=UserOut, dependencies=[Depends(require_role(UserRole.admin))])
async def update_user(user_id: str, payload: UserUpdateRequest, db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(User).where(User.id == user_id))
    user = result.scalar_one_or_none()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    if payload.role is not None:
        user.role = UserRole(payload.role)
    if payload.is_verified is not None:
        user.is_verified = payload.is_verified

    await db.commit()
    await db.refresh(user)
    return user