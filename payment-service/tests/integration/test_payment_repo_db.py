# /tests/integration/test_payment_repo_db.py
from uuid import uuid4
from decimal import Decimal
from datetime import datetime, timezone, timedelta

import pytest
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.models.payment import Payment, PaymentStatuses
from app.repositories.db_payment_repo import DbPaymentRepo
from app.services.payment_service import PaymentService


@pytest.fixture()
def repo(db: Session) -> DbPaymentRepo:
    return DbPaymentRepo(db)


def new_payment(order_id=None, minutes: int = 0) -> Payment:
    return Payment(id=uuid4(), order_id=order_id or uuid4(), amount=Decimal('2500.00'),
                   created_at=datetime(2026, 10, 1, tzinfo=timezone.utc) + timedelta(minutes=minutes))


def test_empty_list(repo: DbPaymentRepo) -> None:
    assert repo.get_payments() == []


def test_create_and_get(repo: DbPaymentRepo) -> None:
    payment = new_payment()
    assert repo.create_payment(payment) == payment
    assert repo.get_payment(payment.id) == payment      # Decimal сохранён без потерь


def test_create_repeat(repo: DbPaymentRepo) -> None:
    payment = new_payment()
    repo.create_payment(payment)
    with pytest.raises(KeyError):
        repo.create_payment(payment)


def test_one_payment_per_order(repo: DbPaymentRepo, db: Session) -> None:
    order_id = uuid4()
    repo.create_payment(new_payment(order_id))
    with pytest.raises(IntegrityError):
        repo.create_payment(new_payment(order_id))
    db.rollback()


def test_get_not_found(repo: DbPaymentRepo) -> None:
    with pytest.raises(KeyError):
        repo.get_payment(uuid4())


def test_find_by_order(repo: DbPaymentRepo) -> None:
    payment = new_payment()
    repo.create_payment(payment)
    assert repo.find_by_order(payment.order_id) == payment
    assert repo.find_by_order(uuid4()) is None


def test_save_payment(repo: DbPaymentRepo) -> None:
    payment = new_payment()
    repo.create_payment(payment)
    payment.status = PaymentStatuses.CONFIRMED
    repo.save_payment(payment)
    assert repo.get_payment(payment.id).status == PaymentStatuses.CONFIRMED


def test_save_unknown_payment(repo: DbPaymentRepo) -> None:
    with pytest.raises(KeyError):
        repo.save_payment(new_payment())


def test_sorting_and_pagination(repo: DbPaymentRepo) -> None:
    third, first, second = new_payment(minutes=30), new_payment(minutes=10), new_payment(minutes=20)
    for payment in (third, first, second):
        repo.create_payment(payment)
    assert [p.id for p in repo.get_payments()] == [first.id, second.id, third.id]
    assert [p.id for p in repo.get_payments(offset=1, count=1)] == [second.id]
    assert [p.id for p in repo.get_payments(order_id=third.order_id)] == [third.id]


def test_service_confirm_and_refund_with_db(repo: DbPaymentRepo) -> None:
    """Бизнес-логика поверх настоящей БД."""
    service = PaymentService(repo)
    order_id = uuid4()
    service.handle_order_created({'order_id': str(order_id), 'total': '2500.00'})
    payment = repo.find_by_order(order_id)
    service.confirm_payment(payment.id)
    service.handle_order_canceled({'order_id': str(order_id), 'refund_required': True})
    assert repo.get_payment(payment.id).status == PaymentStatuses.REFUNDED
