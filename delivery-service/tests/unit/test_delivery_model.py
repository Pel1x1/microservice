# /tests/unit/test_delivery_model.py
from uuid import uuid4
from datetime import datetime, timezone

import pytest
from pydantic import ValidationError

from app.models.delivery import Delivery, DeliveryStatuses


def test_delivery_creation() -> None:
    delivery_id, order_id = uuid4(), uuid4()
    created_at = datetime.now(timezone.utc)
    delivery = Delivery(id=delivery_id, order_id=order_id, address='Москва', created_at=created_at)
    assert dict(delivery) == {'id': delivery_id, 'order_id': order_id, 'address': 'Москва',
                              'status': DeliveryStatuses.ASSIGNED, 'created_at': created_at}


def test_delivery_address_required() -> None:
    with pytest.raises(ValidationError):
        Delivery(id=uuid4(), order_id=uuid4(), address='', created_at=datetime.now(timezone.utc))


def test_delivery_order_required() -> None:
    with pytest.raises(ValidationError):
        Delivery(id=uuid4(), address='a', created_at=datetime.now(timezone.utc))


def test_delivery_assignment_is_validated() -> None:
    delivery = Delivery(id=uuid4(), order_id=uuid4(), address='a', created_at=datetime.now(timezone.utc))
    with pytest.raises(ValidationError):
        delivery.status = 'lost'
