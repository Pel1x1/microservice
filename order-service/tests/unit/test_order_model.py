# /tests/unit/test_order_model.py
from uuid import uuid4
from decimal import Decimal
from datetime import datetime, timezone

import pytest
from pydantic import ValidationError

from app.models.order import Order, OrderItem, OrderStatuses, CreateOrderRequest


@pytest.fixture()
def items() -> list[OrderItem]:
    return [OrderItem(part_id=uuid4(), quantity=2, price=Decimal('2500.00')),
            OrderItem(part_id=uuid4(), quantity=1, price=Decimal('600.50'))]


def test_order_creation(items: list[OrderItem]) -> None:
    order_id, customer_id = uuid4(), uuid4()
    created_at = datetime.now(timezone.utc)
    order = Order(id=order_id, customer_id=customer_id, address='Москва, пр. Вернадского, 78',
                  items=items, status=OrderStatuses.CREATED, created_at=created_at)
    assert dict(order) == {'id': order_id, 'customer_id': customer_id,
                           'address': 'Москва, пр. Вернадского, 78', 'items': items,
                           'status': OrderStatuses.CREATED, 'created_at': created_at}


def test_order_total(items: list[OrderItem]) -> None:
    order = Order(id=uuid4(), customer_id=uuid4(), address='a', items=items,
                  status=OrderStatuses.CREATED, created_at=datetime.now(timezone.utc))
    assert order.total == Decimal('5600.50')


def test_order_items_required() -> None:
    with pytest.raises(ValidationError):
        Order(id=uuid4(), customer_id=uuid4(), address='a', items=[],
              status=OrderStatuses.CREATED, created_at=datetime.now(timezone.utc))


def test_order_address_required(items: list[OrderItem]) -> None:
    with pytest.raises(ValidationError):
        Order(id=uuid4(), customer_id=uuid4(), address='', items=items,
              status=OrderStatuses.CREATED, created_at=datetime.now(timezone.utc))


def test_order_status_required(items: list[OrderItem]) -> None:
    with pytest.raises(ValidationError):
        Order(id=uuid4(), customer_id=uuid4(), address='a', items=items,
              created_at=datetime.now(timezone.utc))


def test_order_item_quantity_positive() -> None:
    with pytest.raises(ValidationError):
        OrderItem(part_id=uuid4(), quantity=0, price=Decimal('1.00'))


def test_create_request_parses_json() -> None:
    part_id, customer_id = uuid4(), uuid4()
    request = CreateOrderRequest.model_validate({
        'customer_id': str(customer_id), 'address': 'a',
        'items': [{'part_id': str(part_id), 'quantity': 3}]})
    assert request.items[0].part_id == part_id
    assert request.items[0].quantity == 3
