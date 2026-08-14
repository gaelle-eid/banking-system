import re
from datetime import date
from pydantic import BaseModel, EmailStr, field_validator, Field
from app.models.models import UserRole
from datetime import datetime as dt


class UserRegister(BaseModel):
    email: EmailStr
    password: str
    full_name: str
    phone: str
    date_of_birth: date
    address: str
    national_id: str
    accepted_terms: bool
    role: UserRole = UserRole.client

    @field_validator("password")
    @classmethod
    def validate_password(cls, v: str) -> str:
        if len(v) < 8:
            raise ValueError("Password must be at least 8 characters long")
        if not re.search(r"[A-Z]", v):
            raise ValueError("Password must contain at least one uppercase letter")
        if not re.search(r"[a-z]", v):
            raise ValueError("Password must contain at least one lowercase letter")
        if not re.search(r"\d", v):
            raise ValueError("Password must contain at least one number")
        if not re.search(r"[!@#$%^&*(),.?\":{}|<>]", v):
            raise ValueError("Password must contain at least one special character")
        return v

    @field_validator("phone")
    @classmethod
    def validate_phone(cls, v: str) -> str:
        cleaned = re.sub(r"[\s\-()]", "", v)
        if not re.match(r"^\+?\d{7,15}$", cleaned):
            raise ValueError("Phone number must be 7-15 digits, optionally starting with +")
        return cleaned

    @field_validator("date_of_birth")
    @classmethod
    def validate_age(cls, v: date) -> date:
        today = date.today()
        age = today.year - v.year - ((today.month, today.day) < (v.month, v.day))
        if age < 18:
            raise ValueError("You must be at least 18 years old to register")
        if age > 120:
            raise ValueError("Please enter a valid date of birth")
        return v

    @field_validator("accepted_terms")
    @classmethod
    def validate_terms(cls, v: bool) -> bool:
        if not v:
            raise ValueError("You must accept the terms and conditions")
        return v

    @field_validator("national_id")
    @classmethod
    def validate_national_id(cls, v: str) -> str:
        if len(v.strip()) < 4:
            raise ValueError("National ID must be at least 4 characters")
        return v.strip()


class UserLogin(BaseModel):
    email: EmailStr
    password: str


class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"


class UserOut(BaseModel):
    id: str
    email: str
    full_name: str
    phone: str | None
    phone_verified: bool = False
    address: str | None
    date_of_birth: dt | None = None
    national_id_masked: str | None = None
    role: UserRole
    is_verified: bool = False
    registration_status: str | None = None
    last_login_at: dt | None

    class Config:
        from_attributes = True


class VerifyResponse(BaseModel):
    message: str


class ProfileUpdateRequest(BaseModel):
    phone: str | None = None
    address: str | None = None


class ChangePasswordRequest(BaseModel):
    current_password: str
    new_password: str = Field(min_length=8)

    @field_validator("new_password")
    @classmethod
    def validate_new_password(cls, v: str) -> str:
        if len(v) < 8:
            raise ValueError("Password must be at least 8 characters long")
        if not re.search(r"[A-Z]", v):
            raise ValueError("Password must contain at least one uppercase letter")
        if not re.search(r"[a-z]", v):
            raise ValueError("Password must contain at least one lowercase letter")
        if not re.search(r"\d", v):
            raise ValueError("Password must contain at least one number")
        if not re.search(r"[!@#$%^&*(),.?\":{}|<>]", v):
            raise ValueError("Password must contain at least one special character")
        return v


class ResendVerificationRequest(BaseModel):
    email: EmailStr


class SendPhoneOtpRequest(BaseModel):
    pass


class VerifyPhoneOtpRequest(BaseModel):
    otp: str