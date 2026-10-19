# /tests/unit/test_review_service.py
from uuid import uuid4, UUID

import pytest

from app.repositories.local_review_repo import LocalReviewRepo
from app.services.review_service import ReviewService
from tests.unit.fakes import FakeOrderClient


@pytest.fixture()
def orders() -> FakeOrderClient:
    return FakeOrderClient()


@pytest.fixture()
def service(orders: FakeOrderClient) -> ReviewService:
    # Dependency injection: локальный репозиторий и мок order-service
    return ReviewService(LocalReviewRepo(), orders)


@pytest.fixture()
def buyer_id() -> UUID:
    return uuid4()


@pytest.fixture()
def part_id() -> UUID:
    return uuid4()


@pytest.fixture()
def order_id(orders: FakeOrderClient, buyer_id: UUID, part_id: UUID) -> UUID:
    order_id = uuid4()
    orders.add(order_id, buyer_id, [part_id], 'completed')
    return order_id


def test_empty_reviews(service: ReviewService) -> None:
    assert service.get_reviews() == []


def test_create_review(service: ReviewService, order_id: UUID, part_id: UUID, buyer_id: UUID) -> None:
    review = service.create_review(order_id, part_id, buyer_id, 5, 'Отлично')
    assert review.rating == 5
    assert review.text == 'Отлично'
    assert service.get_review(review.id) == review


def test_create_review_unknown_order(service: ReviewService, part_id: UUID, buyer_id: UUID) -> None:
    with pytest.raises(ValueError):
        service.create_review(uuid4(), part_id, buyer_id, 5)
    assert service.get_reviews() == []


def test_create_review_foreign_order(service: ReviewService, order_id: UUID, part_id: UUID) -> None:
    with pytest.raises(ValueError):
        service.create_review(order_id, part_id, uuid4(), 5)


@pytest.mark.parametrize('status', ['created', 'confirmed', 'assembled', 'canceled'])
def test_create_review_order_not_completed(service: ReviewService, orders: FakeOrderClient,
                                           part_id: UUID, buyer_id: UUID, status: str) -> None:
    order_id = uuid4()
    orders.add(order_id, buyer_id, [part_id], status)
    with pytest.raises(ValueError):
        service.create_review(order_id, part_id, buyer_id, 5)


def test_create_review_part_not_in_order(service: ReviewService, order_id: UUID,
                                         buyer_id: UUID) -> None:
    with pytest.raises(ValueError):
        service.create_review(order_id, uuid4(), buyer_id, 5)


def test_create_review_order_service_unavailable(service: ReviewService, orders: FakeOrderClient,
                                                 order_id: UUID, part_id: UUID, buyer_id: UUID) -> None:
    orders.available = False
    with pytest.raises(ConnectionError):
        service.create_review(order_id, part_id, buyer_id, 5)


def test_create_review_twice_forbidden(service: ReviewService, order_id: UUID, part_id: UUID,
                                       buyer_id: UUID) -> None:
    service.create_review(order_id, part_id, buyer_id, 5)
    with pytest.raises(ValueError):
        service.create_review(order_id, part_id, buyer_id, 1)


def test_get_review_not_found(service: ReviewService) -> None:
    with pytest.raises(KeyError):
        service.get_review(uuid4())


def test_rating_without_reviews(service: ReviewService, part_id: UUID) -> None:
    rating = service.get_rating(part_id)
    assert (rating.count, rating.average) == (0, None)


def test_rating_is_average(service: ReviewService, orders: FakeOrderClient, part_id: UUID) -> None:
    for stars in (5, 4, 4):
        buyer_id, order_id = uuid4(), uuid4()
        orders.add(order_id, buyer_id, [part_id])
        service.create_review(order_id, part_id, buyer_id, stars)
    rating = service.get_rating(part_id)
    assert rating.count == 3
    assert rating.average == 4.33


def test_filter_and_pagination(service: ReviewService, orders: FakeOrderClient) -> None:
    part_id, other_part = uuid4(), uuid4()
    mine = []
    for _ in range(3):
        buyer_id, order_id = uuid4(), uuid4()
        orders.add(order_id, buyer_id, [part_id, other_part])
        mine.append(service.create_review(order_id, part_id, buyer_id, 5))
    buyer_id, order_id = uuid4(), uuid4()
    orders.add(order_id, buyer_id, [other_part])
    service.create_review(order_id, other_part, buyer_id, 3)
    assert len(service.get_reviews()) == 4
    assert [r.id for r in service.get_reviews(part_id=part_id, offset=1, count=1)] == [mine[1].id]
