import re
from datetime import date
from pydantic import BaseModel, EmailStr, field_validator
from app.models.models import UserRole


class UserRegister(BaseModel):
    email: EmailStr
    password: str
    full_name: str
    phone: str
    date_of_birth: date
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
    role: UserRole

    class Config:
        from_attributes = True