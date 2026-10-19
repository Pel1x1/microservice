# /tests/integration/test_delivery_repo_db.py
from uuid import uuid4
from datetime import datetime, timezone, timedelta

import pytest
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.models.delivery import Delivery, DeliveryStatuses
from app.repositories.db_delivery_repo import DbDeliveryRepo
from app.services.delivery_service import DeliveryService


@pytest.fixture()
def repo(db: Session) -> DbDeliveryRepo:
    return DbDeliveryRepo(db)


def new_delivery(order_id=None, minutes: int = 0) -> Delivery:
    return Delivery(id=uuid4(), order_id=order_id or uuid4(), address='Москва',
                    created_at=datetime(2026, 10, 1, tzinfo=timezone.utc) + timedelta(minutes=minutes))


def test_empty_list(repo: DbDeliveryRepo) -> None:
    assert repo.get_deliveries() == []


def test_create_and_get(repo: DbDeliveryRepo) -> None:
    delivery = new_delivery()
    assert repo.create_delivery(delivery) == delivery
    assert repo.get_delivery(delivery.id) == delivery


def test_create_repeat(repo: DbDeliveryRepo) -> None:
    delivery = new_delivery()
    repo.create_delivery(delivery)
    with pytest.raises(KeyError):
        repo.create_delivery(delivery)


def test_one_delivery_per_order(repo: DbDeliveryRepo, db: Session) -> None:
    order_id = uuid4()
    repo.create_delivery(new_delivery(order_id))
    with pytest.raises(IntegrityError):
        repo.create_delivery(new_delivery(order_id))
    db.rollback()


def test_get_not_found(repo: DbDeliveryRepo) -> None:
    with pytest.raises(KeyError):
        repo.get_delivery(uuid4())


def test_find_by_order(repo: DbDeliveryRepo) -> None:
    delivery = new_delivery()
    repo.create_delivery(delivery)
    assert repo.find_by_order(delivery.order_id) == delivery
    assert repo.find_by_order(uuid4()) is None


def test_save_delivery(repo: DbDeliveryRepo) -> None:
    delivery = new_delivery()
    repo.create_delivery(delivery)
    delivery.status = DeliveryStatuses.IN_TRANSIT
    repo.save_delivery(delivery)
    assert repo.get_delivery(delivery.id).status == DeliveryStatuses.IN_TRANSIT


def test_save_unknown_delivery(repo: DbDeliveryRepo) -> None:
    with pytest.raises(KeyError):
        repo.save_delivery(new_delivery())


def test_sorting_and_pagination(repo: DbDeliveryRepo) -> None:
    third, first, second = new_delivery(minutes=30), new_delivery(minutes=10), new_delivery(minutes=20)
    for delivery in (third, first, second):
        repo.create_delivery(delivery)
    assert [d.id for d in repo.get_deliveries()] == [first.id, second.id, third.id]
    assert [d.id for d in repo.get_deliveries(offset=1, count=1)] == [second.id]
    assert [d.id for d in repo.get_deliveries(order_id=third.order_id)] == [third.id]


def test_service_lifecycle_with_db(repo: DbDeliveryRepo) -> None:
    """Бизнес-логика поверх настоящей БД."""
    service = DeliveryService(repo)
    order_id = uuid4()
    service.handle_order_assembled({'order_id': str(order_id), 'address': 'Москва'})
    delivery = repo.find_by_order(order_id)
    service.ship_delivery(delivery.id)
    service.deliver_delivery(delivery.id)
    assert repo.get_delivery(delivery.id).status == DeliveryStatuses.DELIVERED
