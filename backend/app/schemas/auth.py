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
    address: str
    national_id: str
    accepted_terms: bool
    role: UserRole = UserRole.client

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
    address: str | None
    role: UserRole

    class Config:
        from_attributes = True

    class Config:
        from_attributes = True