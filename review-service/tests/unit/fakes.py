from uuid import UUID

from app.clients.order_client import OrderClient, OrderInfo


class FakeOrderClient(OrderClient):
    """Мок order-service: заказы задаются в тесте."""

    def __init__(self) -> None:
        self.orders: dict[UUID, OrderInfo] = {}
        self.available = True

    def add(self, order_id: UUID, customer_id: UUID, part_ids: list[UUID],
            status: str = 'completed') -> None:
        self.orders[order_id] = OrderInfo(id=order_id, customer_id=customer_id, status=status,
                                          part_ids=part_ids)

    def get_order(self, order_id: UUID) -> OrderInfo:
        if not self.available:
            raise ConnectionError('order-service is unavailable')
        if order_id not in self.orders:
            raise KeyError(order_id)
        return self.orders[order_id]
