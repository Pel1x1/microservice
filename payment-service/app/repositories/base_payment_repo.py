from abc import ABC, abstractmethod
from uuid import UUID

from app.models.payment import Payment


class BasePaymentRepo(ABC):
    @abstractmethod
    def get_payments(self, order_id: UUID | None = None, offset: int = 0,
                     count: int | None = None) -> list[Payment]:
        """Список оплат, отсортированный по дате создания."""

    @abstractmethod
    def get_payment(self, payment_id: UUID) -> Payment:
        """KeyError, если оплаты нет."""

    @abstractmethod
    def find_by_order(self, order_id: UUID) -> Payment | None: ...

    @abstractmethod
    def create_payment(self, payment: Payment) -> Payment:
        """KeyError, если оплата с таким id уже есть."""

    @abstractmethod
    def save_payment(self, payment: Payment) -> Payment:
        """KeyError, если оплаты нет."""
