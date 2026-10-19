# /tests/integration/test_order_repo_db.py
from uuid import uuid4
from decimal import Decimal
from datetime import datetime, timezone, timedelta

import pytest
from sqlalchemy.orm import Session

from app.models.order import Order, OrderItem, OrderStatuses
from app.repositories.db_order_repo import DbOrderRepo


@pytest.fixture()
def repo(db: Session) -> DbOrderRepo:
    return DbOrderRepo(db)


def new_order(customer_id=None, minutes: int = 0) -> Order:
    return Order(id=uuid4(), customer_id=customer_id or uuid4(), address='Москва',
                 items=[OrderItem(part_id=uuid4(), quantity=2, price=Decimal('2500.00'))],
                 status=OrderStatuses.CREATED,
                 created_at=datetime(2026, 10, 1, tzinfo=timezone.utc) + timedelta(minutes=minutes))


def test_empty_list(repo: DbOrderRepo) -> None:
    assert repo.get_orders() == []


def test_create_and_get(repo: DbOrderRepo) -> None:
    order = new_order()
    assert repo.create_order(order) == order
    saved = repo.get_order(order.id)
    assert saved == order                      # позиции (JSON) и Decimal-цены восстановлены
    assert saved.total == Decimal('5000.00')


def test_create_repeat(repo: DbOrderRepo) -> None:
    order = new_order()
    repo.create_order(order)
    with pytest.raises(KeyError):
        repo.create_order(order)


def test_get_not_found(repo: DbOrderRepo) -> None:
    with pytest.raises(KeyError):
        repo.get_order(uuid4())


def test_set_status(repo: DbOrderRepo) -> None:
    order = new_order()
    repo.create_order(order)
    order.status = OrderStatuses.CONFIRMED
    repo.set_status(order)
    assert repo.get_order(order.id).status == OrderStatuses.CONFIRMED


def test_set_status_not_found(repo: DbOrderRepo) -> None:
    with pytest.raises(KeyError):
        repo.set_status(new_order())


def test_filters_sorting_pagination(repo: DbOrderRepo) -> None:
    customer_id = uuid4()
    third, first, second = new_order(customer_id, 30), new_order(customer_id, 10), \
        new_order(customer_id, 20)
    for order in (third, first, second, new_order(minutes=40)):
        repo.create_order(order)
    second.status = OrderStatuses.CANCELED
    repo.set_status(second)

    assert [o.id for o in repo.get_orders(customer_id=customer_id)] == \
        [first.id, second.id, third.id]
    assert [o.id for o in repo.get_orders(customer_id=customer_id, offset=1, count=1)] == \
        [second.id]
    assert [o.id for o in repo.get_orders(status=OrderStatuses.CANCELED)] == [second.id]
    assert len(repo.get_orders()) == 4
