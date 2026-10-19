from uuid import UUID

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.payment import Payment
from app.repositories.base_payment_repo import BasePaymentRepo
from app.schemas.payment import Payment as DBPayment


class DbPaymentRepo(BasePaymentRepo):
    def __init__(self, db: Session) -> None:
        self.db = db

    def get_payments(self, order_id: UUID | None = None, offset: int = 0,
                     count: int | None = None) -> list[Payment]:
        query = select(DBPayment).order_by(DBPayment.created_at)
        if order_id is not None:
            query = query.where(DBPayment.order_id == order_id)
        query = query.offset(offset)
        if count is not None:
            query = query.limit(count)
        return [Payment.model_validate(p) for p in self.db.scalars(query).all()]

    def get_payment(self, payment_id: UUID) -> Payment:
        payment = self.db.get(DBPayment, payment_id)
        if payment is None:
            raise KeyError(payment_id)
        return Payment.model_validate(payment)

    def find_by_order(self, order_id: UUID) -> Payment | None:
        payment = self.db.scalars(select(DBPayment).where(DBPayment.order_id == order_id)).first()
        return None if payment is None else Payment.model_validate(payment)

    def create_payment(self, payment: Payment) -> Payment:
        if self.db.get(DBPayment, payment.id) is not None:
            raise KeyError(payment.id)
        self.db.add(DBPayment(**payment.model_dump()))
        self.db.commit()
        return payment

    def save_payment(self, payment: Payment) -> Payment:
        db_payment = self.db.get(DBPayment, payment.id)
        if db_payment is None:
            raise KeyError(payment.id)
        db_payment.status = payment.status
        self.db.commit()
        return payment
