# /tests/unit/test_payment_service.py
from uuid import uuid4, UUID
from decimal import Decimal

import pytest

from app.models.payment import PaymentStatuses
from app.repositories.local_payment_repo import LocalPaymentRepo
from app.services.payment_service import PaymentService
from tests.unit.fakes import FakePublisher


@pytest.fixture()
def publisher() -> FakePublisher:
    return FakePublisher()


@pytest.fixture()
def service(publisher: FakePublisher) -> PaymentService:
    return PaymentService(LocalPaymentRepo(), publisher)


@pytest.fixture()
def order_id() -> UUID:
    return uuid4()


def created(order_id: UUID, total: str = '5000.00') -> dict:
    """Событие order.created, как его публикует order-service."""
    return {'order_id': str(order_id), 'customer_id': str(uuid4()), 'address': 'Москва',
            'total': total, 'items': []}


def test_empty_payments(service: PaymentService) -> None:
    assert service.get_payments() == []


def test_order_created_creates_pending_payment(service: PaymentService, order_id: UUID) -> None:
    service.handle_order_created(created(order_id))
    [payment] = service.get_payments(order_id=order_id)
    assert payment.status == PaymentStatuses.PENDING
    assert payment.amount == Decimal('5000.00')
    assert service.get_payment(payment.id) == payment


def test_order_created_twice_is_idempotent(service: PaymentService, order_id: UUID) -> None:
    service.handle_order_created(created(order_id))
    service.handle_order_created(created(order_id))
    assert len(service.get_payments()) == 1


def test_get_payment_not_found(service: PaymentService) -> None:
    with pytest.raises(KeyError):
        service.get_payment(uuid4())


def test_confirm_payment(service: PaymentService, publisher: FakePublisher, order_id: UUID) -> None:
    payment = service.create_payment(order_id, Decimal('100.00'))
    confirmed = service.confirm_payment(payment.id)
    assert confirmed.status == PaymentStatuses.CONFIRMED
    assert publisher.events == [('payment.confirmed', {'order_id': str(order_id),
                                                       'payment_id': str(payment.id)})]


def test_confirm_twice_forbidden(service: PaymentService, order_id: UUID) -> None:
    payment = service.create_payment(order_id, Decimal('100.00'))
    service.confirm_payment(payment.id)
    with pytest.raises(ValueError):
        service.confirm_payment(payment.id)


def test_confirm_unknown_payment(service: PaymentService) -> None:
    with pytest.raises(KeyError):
        service.confirm_payment(uuid4())


def test_fail_payment(service: PaymentService, publisher: FakePublisher, order_id: UUID) -> None:
    payment = service.create_payment(order_id, Decimal('100.00'))
    assert service.fail_payment(payment.id).status == PaymentStatuses.FAILED
    assert publisher.keys() == ['payment.failed']


def test_confirm_after_fail_forbidden(service: PaymentService, order_id: UUID) -> None:
    payment = service.create_payment(order_id, Decimal('100.00'))
    service.fail_payment(payment.id)
    with pytest.raises(ValueError):
        service.confirm_payment(payment.id)


def test_cancel_unpaid_order_closes_payment(service: PaymentService, publisher: FakePublisher,
                                            order_id: UUID) -> None:
    payment = service.create_payment(order_id, Decimal('100.00'))
    service.handle_order_canceled({'order_id': str(order_id), 'reason': None, 'refund_required': False})
    assert service.get_payment(payment.id).status == PaymentStatuses.FAILED
    assert publisher.events == []
    with pytest.raises(ValueError):          # оплатить отменённый заказ уже нельзя
        service.confirm_payment(payment.id)


def test_cancel_paid_order_refunds(service: PaymentService, publisher: FakePublisher,
                                   order_id: UUID) -> None:
    payment = service.create_payment(order_id, Decimal('100.00'))
    service.confirm_payment(payment.id)
    service.handle_order_canceled({'order_id': str(order_id), 'reason': 'передумал',
                                   'refund_required': True})
    assert service.get_payment(payment.id).status == PaymentStatuses.REFUNDED
    assert publisher.events[-1] == ('payment.refunded', {'order_id': str(order_id),
                                                         'payment_id': str(payment.id)})


def test_cancel_paid_order_without_refund_flag_keeps_payment(service: PaymentService,
                                                             order_id: UUID) -> None:
    payment = service.create_payment(order_id, Decimal('100.00'))
    service.confirm_payment(payment.id)
    service.handle_order_canceled({'order_id': str(order_id), 'refund_required': False})
    assert service.get_payment(payment.id).status == PaymentStatuses.CONFIRMED


def test_cancel_unknown_order_is_ignored(service: PaymentService) -> None:
    service.handle_order_canceled({'order_id': str(uuid4()), 'refund_required': True})  # не падает


def test_filter_and_pagination(service: PaymentService) -> None:
    payments = [service.create_payment(uuid4(), Decimal('10.00')) for _ in range(3)]
    assert len(service.get_payments()) == 3
    assert [p.id for p in service.get_payments(offset=1, count=1)] == [payments[1].id]
    assert [p.id for p in service.get_payments(order_id=payments[2].order_id)] == [payments[2].id]
