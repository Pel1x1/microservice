from uuid import UUID

from app.models.payment import Payment
from app.repositories.base_payment_repo import BasePaymentRepo


class LocalPaymentRepo(BasePaymentRepo):
    def __init__(self) -> None:
        self._payments: dict[UUID, Payment] = {}

    def get_payments(self, order_id: UUID | None = None, offset: int = 0,
                     count: int | None = None) -> list[Payment]:
        payments = sorted(self._payments.values(), key=lambda p: p.created_at)
        payments = [p.model_copy() for p in payments if order_id is None or p.order_id == order_id]
        end = None if count is None else offset + count
        return payments[offset:end]

    def get_payment(self, payment_id: UUID) -> Payment:
        if payment_id not in self._payments:
            raise KeyError(payment_id)
        return self._payments[payment_id].model_copy()

    def find_by_order(self, order_id: UUID) -> Payment | None:
        return next((p.model_copy() for p in self._payments.values() if p.order_id == order_id), None)

    def create_payment(self, payment: Payment) -> Payment:
        if payment.id in self._payments:
            raise KeyError(payment.id)
        self._payments[payment.id] = payment.model_copy()
        return payment

    def save_payment(self, payment: Payment) -> Payment:
        if payment.id not in self._payments:
            raise KeyError(payment.id)
        self._payments[payment.id] = payment.model_copy()
        return payment
