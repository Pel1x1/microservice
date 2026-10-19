# /tests/unit/test_payment_model.py
from uuid import uuid4
from decimal import Decimal
from datetime import datetime, timezone

import pytest
from pydantic import ValidationError

from app.models.payment import Payment, PaymentStatuses


def make_payment(**kwargs) -> Payment:
    data = dict(id=uuid4(), order_id=uuid4(), amount=Decimal('5000.00'),
                created_at=datetime.now(timezone.utc))
    return Payment(**{**data, **kwargs})


def test_payment_creation() -> None:
    payment_id, order_id = uuid4(), uuid4()
    created_at = datetime.now(timezone.utc)
    payment = Payment(id=payment_id, order_id=order_id, amount=Decimal('5000.00'), created_at=created_at)
    assert dict(payment) == {'id': payment_id, 'order_id': order_id, 'amount': Decimal('5000.00'),
                             'status': PaymentStatuses.PENDING, 'created_at': created_at}


def test_payment_amount_positive() -> None:
    with pytest.raises(ValidationError):
        make_payment(amount=Decimal('0'))


def test_payment_amount_two_decimals() -> None:
    with pytest.raises(ValidationError):
        make_payment(amount=Decimal('10.123'))


def test_payment_order_required() -> None:
    with pytest.raises(ValidationError):
        Payment(id=uuid4(), amount=Decimal('1.00'), created_at=datetime.now(timezone.utc))


def test_payment_assignment_is_validated() -> None:
    payment = make_payment()
    with pytest.raises(ValidationError):
        payment.status = 'paid'
