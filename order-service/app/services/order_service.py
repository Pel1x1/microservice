from uuid import UUID, uuid4
from datetime import datetime, timezone
from collections import defaultdict

from app.models.order import Order, OrderItem, OrderStatuses, CreateOrderItem
from app.repositories.base_order_repo import BaseOrderRepo
from app.clients.inventory_client import InventoryClient
from app.clients.publisher import EventPublisher


class OrderService:
    """Бизнес-логика контекста «Управление заказами».

    KeyError        — заказ не найден;
    ValueError      — нарушено бизнес-правило (недопустимый переход статуса, нет товара);
    ConnectionError — недоступен inventory-service.
    """

    def __init__(self, order_repo: BaseOrderRepo, inventory: InventoryClient,
                 publisher: EventPublisher | None = None) -> None:
        self.order_repo = order_repo
        self.inventory = inventory
        self.publisher = publisher

    def get_orders(self, customer_id: UUID | None = None, status: OrderStatuses | None = None,
                   offset: int = 0, count: int | None = None) -> list[Order]:
        return self.order_repo.get_orders(customer_id, status, offset, count)

    def get_order(self, order_id: UUID) -> Order:
        return self.order_repo.get_order(order_id)

    def create_order(self, customer_id: UUID, address: str,
                     items: list[CreateOrderItem]) -> Order:
        """Команда «Оформить заказ» (покупатель)."""
        # вложенные вызовы: объединение позиций -> запрос в inventory-service по каждой
        order_items = [self._build_item(part_id, qty)
                       for part_id, qty in self._merge_items(items).items()]
        order = Order(id=uuid4(), customer_id=customer_id, address=address, items=order_items,
                      status=OrderStatuses.CREATED, created_at=datetime.now(timezone.utc))
        self.order_repo.create_order(order)
        self._publish('order.created', {
            'order_id': str(order.id),
            'customer_id': str(order.customer_id),
            'address': order.address,
            'total': str(order.total),
            'items': [{'part_id': str(i.part_id), 'quantity': i.quantity} for i in order.items],
        })
        return order

    def confirm_order(self, order_id: UUID) -> Order:
        """Команда «Подтвердить заказ» (система, после «Оплата подтверждена»)."""
        return self._change_status(order_id, {OrderStatuses.CREATED}, OrderStatuses.CONFIRMED)

    def assemble_order(self, order_id: UUID) -> Order:
        """Команда «Собрать заказ» (продавец)."""
        order = self._change_status(order_id, {OrderStatuses.CONFIRMED}, OrderStatuses.ASSEMBLED)
        self._publish('order.assembled', {'order_id': str(order.id), 'address': order.address})
        return order

    def complete_order(self, order_id: UUID) -> Order:
        """Команда «Завершить заказ» (система, после «Посылка доставлена»)."""
        return self._change_status(order_id, {OrderStatuses.ASSEMBLED}, OrderStatuses.COMPLETED)

    def cancel_order(self, order_id: UUID, reason: str | None = None) -> Order:
        """Команда «Отменить заказ» (покупатель/продавец или система)."""
        previous = self.order_repo.get_order(order_id).status
        order = self._change_status(
            order_id, {OrderStatuses.CREATED, OrderStatuses.CONFIRMED, OrderStatuses.ASSEMBLED},
            OrderStatuses.CANCELED)
        self._publish('order.canceled', {
            'order_id': str(order.id),
            'reason': reason,
            # оплаченный заказ -> payment-service оформит возврат
            'refund_required': previous in (OrderStatuses.CONFIRMED, OrderStatuses.ASSEMBLED),
        })
        return order

    # --- обработчики событий из брокера (policy) ---

    def handle_payment_confirmed(self, payload: dict) -> None:
        self.confirm_order(UUID(str(payload['order_id'])))

    def handle_delivery_delivered(self, payload: dict) -> None:
        self.complete_order(UUID(str(payload['order_id'])))

    def handle_reserve_failed(self, payload: dict) -> None:
        self.cancel_order(UUID(str(payload['order_id'])), payload.get('reason'))

    # --- вложенные вспомогательные функции ---

    @staticmethod
    def _merge_items(items: list[CreateOrderItem]) -> dict[UUID, int]:
        merged: dict[UUID, int] = defaultdict(int)
        for item in items:
            merged[item.part_id] += item.quantity
        return dict(merged)

    def _build_item(self, part_id: UUID, quantity: int) -> OrderItem:
        try:
            stock = self.inventory.get_stock(part_id)
        except KeyError:
            raise ValueError(f'Запчасть {part_id} не найдена')
        if stock.available < quantity:
            raise ValueError(f'Недостаточно запчасти {part_id}: доступно {stock.available}')
        return OrderItem(part_id=part_id, quantity=quantity, price=stock.price)

    def _change_status(self, order_id: UUID, allowed: set[OrderStatuses],
                       new_status: OrderStatuses) -> Order:
        order = self.order_repo.get_order(order_id)
        if order.status not in allowed:
            raise ValueError(f'Заказ в статусе {order.status.value} нельзя перевести '
                             f'в {new_status.value}')
        order.status = new_status
        return self.order_repo.set_status(order)

    def _publish(self, routing_key: str, payload: dict) -> None:
        if self.publisher is not None:
            self.publisher.publish(routing_key, payload)
