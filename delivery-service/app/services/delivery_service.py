from uuid import UUID, uuid4
from datetime import datetime, timezone

from app.models.delivery import Delivery, DeliveryStatuses
from app.repositories.base_delivery_repo import BaseDeliveryRepo
from app.clients.publisher import EventPublisher


class DeliveryService:
    """Бизнес-логика контекста «Управление доставкой».

    Доставку физически выполняет внешняя служба доставки; её статусы эмулируют
    команды «Передать в доставку» и «Подтвердить доставку».

    KeyError   — доставка не найдена;
    ValueError — нарушено бизнес-правило (недопустимый переход статуса).
    """

    def __init__(self, delivery_repo: BaseDeliveryRepo, publisher: EventPublisher | None = None) -> None:
        self.delivery_repo = delivery_repo
        self.publisher = publisher

    def get_deliveries(self, order_id: UUID | None = None, offset: int = 0,
                       count: int | None = None) -> list[Delivery]:
        return self.delivery_repo.get_deliveries(order_id, offset, count)

    def get_delivery(self, delivery_id: UUID) -> Delivery:
        return self.delivery_repo.get_delivery(delivery_id)

    def assign_delivery(self, order_id: UUID, address: str) -> Delivery:
        """Команда «Назначить доставку» (система, после «Заказ собран»). Повтор для заказа игнорируется."""
        existing = self.delivery_repo.find_by_order(order_id)
        if existing is not None:
            return existing
        delivery = Delivery(id=uuid4(), order_id=order_id, address=address,
                            status=DeliveryStatuses.ASSIGNED, created_at=datetime.now(timezone.utc))
        self.delivery_repo.create_delivery(delivery)
        self._publish('delivery.assigned', {'order_id': str(order_id), 'delivery_id': str(delivery.id)})
        return delivery

    def ship_delivery(self, delivery_id: UUID) -> Delivery:
        """Команда «Передать в доставку» (продавец отдал посылку службе доставки)."""
        return self._change_status(delivery_id, {DeliveryStatuses.ASSIGNED}, DeliveryStatuses.IN_TRANSIT)

    def deliver_delivery(self, delivery_id: UUID) -> Delivery:
        """Команда «Подтвердить доставку» (служба доставки)."""
        delivery = self._change_status(delivery_id, {DeliveryStatuses.IN_TRANSIT},
                                       DeliveryStatuses.DELIVERED)
        self._publish('delivery.delivered', {'order_id': str(delivery.order_id)})
        return delivery

    # --- обработчики событий из брокера (policy) ---

    def handle_order_assembled(self, payload: dict) -> None:
        """Политика: «Заказ собран» -> «Назначить доставку»."""
        self.assign_delivery(UUID(str(payload['order_id'])), str(payload['address']))

    # --- вложенные вспомогательные функции ---

    def _change_status(self, delivery_id: UUID, allowed: set[DeliveryStatuses],
                       new_status: DeliveryStatuses) -> Delivery:
        delivery = self.delivery_repo.get_delivery(delivery_id)
        if delivery.status not in allowed:
            raise ValueError(f'Доставка в статусе {delivery.status.value} нельзя перевести '
                             f'в {new_status.value}')
        delivery.status = new_status
        return self.delivery_repo.save_delivery(delivery)

    def _publish(self, routing_key: str, payload: dict) -> None:
        if self.publisher is not None:
            self.publisher.publish(routing_key, payload)
