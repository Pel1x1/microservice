from uuid import UUID

from app.models.review import Review
from app.repositories.base_review_repo import BaseReviewRepo


class LocalReviewRepo(BaseReviewRepo):
    def __init__(self) -> None:
        self._reviews: dict[UUID, Review] = {}

    def get_reviews(self, part_id: UUID | None = None, offset: int = 0,
                    count: int | None = None) -> list[Review]:
        reviews = sorted(self._reviews.values(), key=lambda r: r.created_at)
        reviews = [r.model_copy() for r in reviews if part_id is None or r.part_id == part_id]
        end = None if count is None else offset + count
        return reviews[offset:end]

    def get_review(self, review_id: UUID) -> Review:
        if review_id not in self._reviews:
            raise KeyError(review_id)
        return self._reviews[review_id].model_copy()

    def find_review(self, order_id: UUID, part_id: UUID) -> Review | None:
        return next((r.model_copy() for r in self._reviews.values()
                     if r.order_id == order_id and r.part_id == part_id), None)

    def create_review(self, review: Review) -> Review:
        if review.id in self._reviews:
            raise KeyError(review.id)
        self._reviews[review.id] = review.model_copy()
        return review
