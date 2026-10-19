from uuid import UUID

from app.models.order import Order, OrderStatuses
from app.repositories.base_order_repo import BaseOrderRepo


class LocalOrderRepo(BaseOrderRepo):
    def __init__(self) -> None:
        self._orders: dict[UUID, Order] = {}

    def get_orders(self, customer_id: UUID | None = None, status: OrderStatuses | None = None,
                   offset: int = 0, count: int | None = None) -> list[Order]:
        orders = sorted(self._orders.values(), key=lambda o: o.created_at)
        orders = [o.model_copy() for o in orders
                  if (customer_id is None or o.customer_id == customer_id)
                  and (status is None or o.status == status)]
        end = None if count is None else offset + count
        return orders[offset:end]

    def get_order(self, order_id: UUID) -> Order:
        if order_id not in self._orders:
            raise KeyError(order_id)
        return self._orders[order_id].model_copy()

    def create_order(self, order: Order) -> Order:
        if order.id in self._orders:
            raise KeyError(order.id)
        self._orders[order.id] = order.model_copy()
        return order

    def set_status(self, order: Order) -> Order:
        if order.id not in self._orders:
            raise KeyError(order.id)
        self._orders[order.id].status = order.status
        return order
