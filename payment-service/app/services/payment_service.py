from uuid import UUID, uuid4
from decimal import Decimal
from datetime import datetime, timezone

from app.models.payment import Payment, PaymentStatuses
from app.repositories.base_payment_repo import BasePaymentRepo
from app.clients.publisher import EventPublisher


class PaymentService:
    """Бизнес-логика контекста «Управление оплатой».

    Списание денег выполняет внешний эквайринг; его ответ эмулируют команды
    «Подтвердить оплату» и «Отклонить оплату» (webhook эквайринга).

    KeyError   — оплата не найдена;
    ValueError — нарушено бизнес-правило (недопустимый переход статуса).
    """

    def __init__(self, payment_repo: BasePaymentRepo, publisher: EventPublisher | None = None) -> None:
        self.payment_repo = payment_repo
        self.publisher = publisher

    def get_payments(self, order_id: UUID | None = None, offset: int = 0,
                     count: int | None = None) -> list[Payment]:
        return self.payment_repo.get_payments(order_id, offset, count)

    def get_payment(self, payment_id: UUID) -> Payment:
        return self.payment_repo.get_payment(payment_id)

    def create_payment(self, order_id: UUID, amount: Decimal) -> Payment:
        """Команда «Создать оплату» (система, после «Заказ создан»). Повтор для заказа игнорируется."""
        existing = self.payment_repo.find_by_order(order_id)
        if existing is not None:
            return existing
        payment = Payment(id=uuid4(), order_id=order_id, amount=amount,
                          status=PaymentStatuses.PENDING, created_at=datetime.now(timezone.utc))
        return self.payment_repo.create_payment(payment)

    def confirm_payment(self, payment_id: UUID) -> Payment:
        """Команда «Подтвердить оплату» (эквайринг)."""
        payment = self._change_status(payment_id, {PaymentStatuses.PENDING}, PaymentStatuses.CONFIRMED)
        self._publish('payment.confirmed', {'order_id': str(payment.order_id),
                                            'payment_id': str(payment.id)})
        return payment

    def fail_payment(self, payment_id: UUID) -> Payment:
        """Команда «Отклонить оплату» (эквайринг)."""
        payment = self._change_status(payment_id, {PaymentStatuses.PENDING}, PaymentStatuses.FAILED)
        self._publish('payment.failed', {'order_id': str(payment.order_id),
                                         'payment_id': str(payment.id)})
        return payment

    # --- обработчики событий из брокера (policy) ---

    def handle_order_created(self, payload: dict) -> None:
        """Политика: «Заказ создан» -> «Создать оплату»."""
        self.create_payment(UUID(str(payload['order_id'])), Decimal(str(payload['total'])))

    def handle_order_canceled(self, payload: dict) -> None:
        """Политика: «Заказ отменён» -> закрыть неоплаченную оплату или «Оформить возврат»."""
        payment = self.payment_repo.find_by_order(UUID(str(payload['order_id'])))
        if payment is None:
            return
        if payment.status == PaymentStatuses.PENDING:
            payment.status = PaymentStatuses.FAILED
            self.payment_repo.save_payment(payment)
        elif payment.status == PaymentStatuses.CONFIRMED and payload.get('refund_required'):
            payment.status = PaymentStatuses.REFUNDED
            self.payment_repo.save_payment(payment)
            self._publish('payment.refunded', {'order_id': str(payment.order_id),
                                               'payment_id': str(payment.id)})

    # --- вложенные вспомогательные функции ---

    def _change_status(self, payment_id: UUID, allowed: set[PaymentStatuses],
                       new_status: PaymentStatuses) -> Payment:
        payment = self.payment_repo.get_payment(payment_id)
        if payment.status not in allowed:
            raise ValueError(f'Оплата в статусе {payment.status.value} нельзя перевести '
                             f'в {new_status.value}')
        payment.status = new_status
        return self.payment_repo.save_payment(payment)

    def _publish(self, routing_key: str, payload: dict) -> None:
        if self.publisher is not None:
            self.publisher.publish(routing_key, payload)
