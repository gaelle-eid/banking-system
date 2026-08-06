from pydantic import BaseModel, EmailStr
from datetime import date, datetime
from app.models.models import EmployeeStatus


class EmployeeCreateRequest(BaseModel):
    email: EmailStr
    password: str
    full_name: str
    phone: str
    employee_id: str
    department: str
    branch: str
    job_title: str
    hire_date: date


class EmployeeProfileOut(BaseModel):
    id: str
    user_id: str
    employee_id: str
    department: str
    branch: str
    job_title: str
    hire_date: datetime
    status: EmployeeStatus
    created_at: datetime

    class Config:
        from_attributes = True


class EmployeeOut(BaseModel):
    id: str
    email: str
    full_name: str
    phone: str | None
    role: str
    profile: EmployeeProfileOut | None = None

    class Config:
        from_attributes = True


class UserUpdateRequest(BaseModel):
    role: str | None = None
    is_verified: bool | None = None


class EmployeeStatusUpdateRequest(BaseModel):
    status: EmployeeStatus