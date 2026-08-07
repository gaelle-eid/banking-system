import secrets
from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from app.core.database import get_db
from app.core.security import hash_password, verify_password, create_access_token
from app.core.deps import get_current_user
from app.core.config import settings
from app.core.email import send_verification_email, send_welcome_email
from app.models.models import User
from app.schemas.auth import (
    UserRegister, UserLogin, TokenResponse, UserOut,
    VerifyResponse, ResendVerificationRequest,
)

router = APIRouter(prefix="/auth", tags=["auth"])


@router.post("/register", response_model=UserOut, status_code=status.HTTP_201_CREATED)
async def register(payload: UserRegister, db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(User).where(User.email == payload.email))
    if result.scalar_one_or_none():
        raise HTTPException(status_code=400, detail="Email already registered")

    token = secrets.token_urlsafe(32)

    user = User(
        email=payload.email,
        password_hash=hash_password(payload.password),
        full_name=payload.full_name,
        phone=payload.phone,
        date_of_birth=payload.date_of_birth,
        address=payload.address,
        national_id=payload.national_id,
        role=payload.role,
        is_verified=False,
        verification_token=token,
    )
    db.add(user)
    await db.commit()
    await db.refresh(user)

    try:
        send_verification_email(user.email, user.full_name, token, settings.frontend_url)
    except Exception:
        pass

    return user


@router.get("/verify", response_model=VerifyResponse)
async def verify_email(token: str, db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(User).where(User.verification_token == token))
    user = result.scalar_one_or_none()
    if not user:
        raise HTTPException(status_code=400, detail="Invalid or expired verification token")

    if user.is_verified:
        return VerifyResponse(message="Email already verified. You can log in.")

    user.is_verified = True
    user.verification_token = None
    await db.commit()

    try:
        send_welcome_email(user.email, user.full_name)
    except Exception:
        pass

    return VerifyResponse(message="Email verified successfully. You can now log in.")


@router.post("/resend-verification", response_model=VerifyResponse)
async def resend_verification(payload: ResendVerificationRequest, db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(User).where(User.email == payload.email))
    user = result.scalar_one_or_none()
    if not user:
        return VerifyResponse(message="If that email exists, a verification link has been sent.")

    if user.is_verified:
        return VerifyResponse(message="This email is already verified.")

    token = secrets.token_urlsafe(32)
    user.verification_token = token
    await db.commit()

    try:
        send_verification_email(user.email, user.full_name, token, settings.frontend_url)
    except Exception:
        pass

    return VerifyResponse(message="If that email exists, a verification link has been sent.")


@router.post("/login", response_model=TokenResponse)
async def login(payload: UserLogin, db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(User).where(User.email == payload.email))
    user = result.scalar_one_or_none()

    if not user or not verify_password(payload.password, user.password_hash):
        raise HTTPException(status_code=401, detail="Invalid email or password")

    if not user.is_verified:
        raise HTTPException(status_code=403, detail="Please verify your email before logging in")

    if user.role.value == "employee":
        from app.models.models import EmployeeProfile, EmployeeStatus
        profile_result = await db.execute(select(EmployeeProfile).where(EmployeeProfile.user_id == user.id))
        profile = profile_result.scalar_one_or_none()
        if profile and profile.status == EmployeeStatus.terminated:
            raise HTTPException(status_code=403, detail="This employee account has been terminated")

    user.last_login_at = datetime.utcnow()
    await db.commit()

    token = create_access_token(data={"sub": user.id, "role": user.role.value})
    return TokenResponse(access_token=token)


@router.get("/me", response_model=UserOut)
async def get_me(current_user: User = Depends(get_current_user)):
    return current_user