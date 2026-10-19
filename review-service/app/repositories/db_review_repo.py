from uuid import UUID

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.review import Review
from app.repositories.base_review_repo import BaseReviewRepo
from app.schemas.review import Review as DBReview


class DbReviewRepo(BaseReviewRepo):
    def __init__(self, db: Session) -> None:
        self.db = db

    def get_reviews(self, part_id: UUID | None = None, offset: int = 0,
                    count: int | None = None) -> list[Review]:
        query = select(DBReview).order_by(DBReview.created_at)
        if part_id is not None:
            query = query.where(DBReview.part_id == part_id)
        query = query.offset(offset)
        if count is not None:
            query = query.limit(count)
        return [Review.model_validate(r) for r in self.db.scalars(query).all()]

    def get_review(self, review_id: UUID) -> Review:
        review = self.db.get(DBReview, review_id)
        if review is None:
            raise KeyError(review_id)
        return Review.model_validate(review)

    def find_review(self, order_id: UUID, part_id: UUID) -> Review | None:
        review = self.db.scalars(select(DBReview).where(
            DBReview.order_id == order_id, DBReview.part_id == part_id)).first()
        return None if review is None else Review.model_validate(review)

    def create_review(self, review: Review) -> Review:
        if self.db.get(DBReview, review.id) is not None:
            raise KeyError(review.id)
        self.db.add(DBReview(**review.model_dump()))
        self.db.commit()
        return review
