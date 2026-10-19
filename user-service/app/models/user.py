import enum
from uuid import UUID
from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field


class UserRoles(enum.Enum):
    BUYER = 'buyer'      # покупатель
    SELLER = 'seller'    # продавец
    ADMIN = 'admin'      # администратор площадки


class User(BaseModel):
    """Учётная запись пользователя площадки."""
    model_config = ConfigDict(from_attributes=True, validate_assignment=True)

    id: UUID
    email: str = Field(pattern=r'^[^@\s]+@[^@\s]+\.[^@\s]+$')
    name: str = Field(min_length=1)
    role: UserRoles
    is_blocked: bool = False
    created_at: datetime


class RegisterUserRequest(BaseModel):
    email: str = Field(pattern=r'^[^@\s]+@[^@\s]+\.[^@\s]+$')
    name: str = Field(min_length=1)
    role: UserRoles = UserRoles.BUYER
