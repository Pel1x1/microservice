# /tests/unit/test_review_model.py
from uuid import uuid4
from datetime import datetime, timezone

import pytest
from pydantic import ValidationError

from app.models.review import Review, Rating, CreateReviewRequest


def make_review(**kwargs) -> Review:
    data = dict(id=uuid4(), order_id=uuid4(), part_id=uuid4(), author_id=uuid4(), rating=5,
                created_at=datetime.now(timezone.utc))
    return Review(**{**data, **kwargs})


def test_review_creation() -> None:
    review = make_review(text='Отличные колодки')
    assert review.rating == 5
    assert review.text == 'Отличные колодки'


def test_review_text_is_optional() -> None:
    assert make_review().text == ''


@pytest.mark.parametrize('rating', [0, 6, -1])
def test_review_rating_out_of_range(rating: int) -> None:
    with pytest.raises(ValidationError):
        make_review(rating=rating)


def test_review_assignment_is_validated() -> None:
    review = make_review()
    with pytest.raises(ValidationError):
        review.rating = 10


def test_create_request_parses_json() -> None:
    order_id, part_id, author_id = uuid4(), uuid4(), uuid4()
    request = CreateReviewRequest.model_validate({
        'order_id': str(order_id), 'part_id': str(part_id), 'author_id': str(author_id), 'rating': 4})
    assert request.order_id == order_id
    assert request.rating == 4


def test_rating_without_reviews() -> None:
    rating = Rating(part_id=uuid4(), count=0)
    assert rating.average is None
