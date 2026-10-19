import enum
from uuid import UUID
from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field


class PartStatuses(enum.Enum):
    PUBLISHED = 'published'        # карточка видна в каталоге
    UNPUBLISHED = 'unpublished'    # снята с публикации


class Part(BaseModel):
    """Карточка запчасти с привязкой к автомобилям, для которых она подходит."""
    model_config = ConfigDict(from_attributes=True, validate_assignment=True)

    id: UUID
    store_id: UUID
    name: str = Field(min_length=1)
    category: str = Field(min_length=1)
    brand: str = Field(min_length=1)
    compatible_cars: list[str] = Field(min_length=1)
    status: PartStatuses = PartStatuses.PUBLISHED
    created_at: datetime


class PublishPartRequest(BaseModel):
    store_id: UUID
    name: str = Field(min_length=1)
    category: str = Field(min_length=1)
    brand: str = Field(min_length=1)
    compatible_cars: list[str] = Field(min_length=1)
