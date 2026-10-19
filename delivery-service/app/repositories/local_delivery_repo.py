from uuid import UUID

from app.models.delivery import Delivery
from app.repositories.base_delivery_repo import BaseDeliveryRepo


class LocalDeliveryRepo(BaseDeliveryRepo):
    def __init__(self) -> None:
        self._deliveries: dict[UUID, Delivery] = {}

    def get_deliveries(self, order_id: UUID | None = None, offset: int = 0,
                       count: int | None = None) -> list[Delivery]:
        items = sorted(self._deliveries.values(), key=lambda d: d.created_at)
        items = [d.model_copy() for d in items if order_id is None or d.order_id == order_id]
        end = None if count is None else offset + count
        return items[offset:end]

    def get_delivery(self, delivery_id: UUID) -> Delivery:
        if delivery_id not in self._deliveries:
            raise KeyError(delivery_id)
        return self._deliveries[delivery_id].model_copy()

    def find_by_order(self, order_id: UUID) -> Delivery | None:
        return next((d.model_copy() for d in self._deliveries.values() if d.order_id == order_id), None)

    def create_delivery(self, delivery: Delivery) -> Delivery:
        if delivery.id in self._deliveries:
            raise KeyError(delivery.id)
        self._deliveries[delivery.id] = delivery.model_copy()
        return delivery

    def save_delivery(self, delivery: Delivery) -> Delivery:
        if delivery.id not in self._deliveries:
            raise KeyError(delivery.id)
        self._deliveries[delivery.id] = delivery.model_copy()
        return delivery
