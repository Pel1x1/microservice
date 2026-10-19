from abc import ABC, abstractmethod
from uuid import UUID

from app.models.delivery import Delivery


class BaseDeliveryRepo(ABC):
    @abstractmethod
    def get_deliveries(self, order_id: UUID | None = None, offset: int = 0,
                       count: int | None = None) -> list[Delivery]:
        """Список доставок, отсортированный по дате создания."""

    @abstractmethod
    def get_delivery(self, delivery_id: UUID) -> Delivery:
        """KeyError, если доставки нет."""

    @abstractmethod
    def find_by_order(self, order_id: UUID) -> Delivery | None: ...

    @abstractmethod
    def create_delivery(self, delivery: Delivery) -> Delivery:
        """KeyError, если доставка с таким id уже есть."""

    @abstractmethod
    def save_delivery(self, delivery: Delivery) -> Delivery:
        """KeyError, если доставки нет."""
