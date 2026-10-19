from uuid import UUID
from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field


class Review(BaseModel):
    """Отзыв покупателя на запчасть из доставленного заказа."""
    model_config = ConfigDict(from_attributes=True, validate_assignment=True)

    id: UUID
    order_id: UUID
    part_id: UUID
    author_id: UUID
    rating: int = Field(ge=1, le=5)
    text: str = ''
    created_at: datetime


class CreateReviewRequest(BaseModel):
    order_id: UUID
    part_id: UUID
    author_id: UUID
    rating: int = Field(ge=1, le=5)
    text: str = ''


class Rating(BaseModel):
    """Рейтинг запчасти — среднее по её отзывам."""
    part_id: UUID
    count: int = Field(ge=0)
    average: float | None = None
