from abc import ABC, abstractmethod
from uuid import UUID

from app.models.order import Order, OrderStatuses


class BaseOrderRepo(ABC):
    @abstractmethod
    def get_orders(self, customer_id: UUID | None = None, status: OrderStatuses | None = None,
                   offset: int = 0, count: int | None = None) -> list[Order]:
        """Список заказов, отсортированный по дате создания."""

    @abstractmethod
    def get_order(self, order_id: UUID) -> Order:
        """KeyError, если заказа нет."""

    @abstractmethod
    def create_order(self, order: Order) -> Order:
        """KeyError, если заказ с таким id уже есть."""

    @abstractmethod
    def set_status(self, order: Order) -> Order:
        """KeyError, если заказа нет."""
