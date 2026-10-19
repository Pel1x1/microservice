import enum
from uuid import UUID
from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field


class StoreStatuses(enum.Enum):
    PENDING = 'pending'      # создан, ждёт верификации
    VERIFIED = 'verified'    # проверен администратором, может публиковать товары
    BLOCKED = 'blocked'      # заблокирован


class Store(BaseModel):
    """Магазин продавца."""
    model_config = ConfigDict(from_attributes=True, validate_assignment=True)

    id: UUID
    owner_id: UUID
    name: str = Field(min_length=1)
    status: StoreStatuses = StoreStatuses.PENDING
    created_at: datetime


class CreateStoreRequest(BaseModel):
    owner_id: UUID
    name: str = Field(min_length=1)
