# /tests/unit/test_stock_model.py
from uuid import uuid4
from decimal import Decimal

import pytest
from pydantic import ValidationError

from app.models.stock import Stock, Reservation, ReservationStatuses


def test_stock_creation() -> None:
    part_id, store_id = uuid4(), uuid4()
    stock = Stock(part_id=part_id, store_id=store_id, price=Decimal('1500.00'), quantity=10)
    assert dict(stock) == {'part_id': part_id, 'store_id': store_id,
                           'price': Decimal('1500.00'), 'quantity': 10, 'reserved': 0}


def test_stock_available_is_quantity_minus_reserved() -> None:
    stock = Stock(part_id=uuid4(), store_id=uuid4(), price=100, quantity=10, reserved=3)
    assert stock.available == 7
    assert stock.model_dump()['available'] == 7


def test_stock_negative_quantity_forbidden() -> None:
    with pytest.raises(ValidationError):
        Stock(part_id=uuid4(), store_id=uuid4(), price=100, quantity=-1)


def test_stock_zero_price_forbidden() -> None:
    with pytest.raises(ValidationError):
        Stock(part_id=uuid4(), store_id=uuid4(), price=0, quantity=1)


def test_stock_store_required() -> None:
    with pytest.raises(ValidationError):
        Stock(part_id=uuid4(), price=100, quantity=1)


def test_stock_assignment_is_validated() -> None:
    stock = Stock(part_id=uuid4(), store_id=uuid4(), price=100, quantity=1)
    with pytest.raises(ValidationError):
        stock.reserved = -5


def test_reservation_default_status_active() -> None:
    reservation = Reservation(id=uuid4(), order_id=uuid4(), part_id=uuid4(), quantity=1)
    assert reservation.status == ReservationStatuses.ACTIVE


def test_reservation_quantity_must_be_positive() -> None:
    with pytest.raises(ValidationError):
        Reservation(id=uuid4(), order_id=uuid4(), part_id=uuid4(), quantity=0)
