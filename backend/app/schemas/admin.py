from pydantic import BaseModel
from app.models.models import UserRole


class UserUpdateRequest(BaseModel):
    role: UserRole | None = None
    is_verified: bool | None = None