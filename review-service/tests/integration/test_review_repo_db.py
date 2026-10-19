# /tests/integration/test_review_repo_db.py
from uuid import uuid4
from datetime import datetime, timezone, timedelta

import pytest
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.models.review import Review
from app.repositories.db_review_repo import DbReviewRepo
from app.services.review_service import ReviewService
from tests.unit.fakes import FakeOrderClient


@pytest.fixture()
def repo(db: Session) -> DbReviewRepo:
    return DbReviewRepo(db)


def new_review(part_id=None, order_id=None, rating: int = 5, minutes: int = 0) -> Review:
    return Review(id=uuid4(), order_id=order_id or uuid4(), part_id=part_id or uuid4(),
                  author_id=uuid4(), rating=rating, text='Хорошо',
                  created_at=datetime(2026, 10, 1, tzinfo=timezone.utc) + timedelta(minutes=minutes))


def test_empty_list(repo: DbReviewRepo) -> None:
    assert repo.get_reviews() == []


def test_create_and_get(repo: DbReviewRepo) -> None:
    review = new_review()
    assert repo.create_review(review) == review
    assert repo.get_review(review.id) == review


def test_create_repeat(repo: DbReviewRepo) -> None:
    review = new_review()
    repo.create_review(review)
    with pytest.raises(KeyError):
        repo.create_review(review)


def test_one_review_per_order_and_part(repo: DbReviewRepo, db: Session) -> None:
    part_id, order_id = uuid4(), uuid4()
    repo.create_review(new_review(part_id, order_id))
    with pytest.raises(IntegrityError):
        repo.create_review(new_review(part_id, order_id))
    db.rollback()


def test_get_not_found(repo: DbReviewRepo) -> None:
    with pytest.raises(KeyError):
        repo.get_review(uuid4())


def test_find_review(repo: DbReviewRepo) -> None:
    review = new_review()
    repo.create_review(review)
    assert repo.find_review(review.order_id, review.part_id) == review
    assert repo.find_review(review.order_id, uuid4()) is None


def test_filter_sorting_pagination(repo: DbReviewRepo) -> None:
    part_id = uuid4()
    third, first, second = (new_review(part_id, minutes=30), new_review(part_id, minutes=10),
                            new_review(part_id, minutes=20))
    for review in (third, first, second, new_review(minutes=40)):
        repo.create_review(review)
    assert [r.id for r in repo.get_reviews(part_id=part_id)] == [first.id, second.id, third.id]
    assert [r.id for r in repo.get_reviews(part_id=part_id, offset=1, count=1)] == [second.id]
    assert len(repo.get_reviews()) == 4


def test_service_rating_with_db(repo: DbReviewRepo) -> None:
    """Бизнес-логика поверх настоящей БД (order-service замокан)."""
    orders = FakeOrderClient()
    service = ReviewService(repo, orders)
    part_id = uuid4()
    for stars in (5, 3):
        buyer_id, order_id = uuid4(), uuid4()
        orders.add(order_id, buyer_id, [part_id])
        service.create_review(order_id, part_id, buyer_id, stars)
    rating = service.get_rating(part_id)
    assert (rating.count, rating.average) == (2, 4.0)
