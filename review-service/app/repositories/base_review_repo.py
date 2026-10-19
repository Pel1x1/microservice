from abc import ABC, abstractmethod
from uuid import UUID

from app.models.review import Review


class BaseReviewRepo(ABC):
    @abstractmethod
    def get_reviews(self, part_id: UUID | None = None, offset: int = 0,
                    count: int | None = None) -> list[Review]:
        """Список отзывов, отсортированный по дате создания."""

    @abstractmethod
    def get_review(self, review_id: UUID) -> Review:
        """KeyError, если отзыва нет."""

    @abstractmethod
    def find_review(self, order_id: UUID, part_id: UUID) -> Review | None:
        """Отзыв на запчасть из заказа, если он уже оставлен."""

    @abstractmethod
    def create_review(self, review: Review) -> Review:
        """KeyError, если отзыв с таким id уже есть."""
