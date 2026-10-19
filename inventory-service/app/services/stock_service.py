from uuid import UUID, uuid4
from decimal import Decimal
from collections import defaultdict

from app.models.stock import Stock, Reservation, ReservationStatuses, ReserveItem
from app.repositories.base_stock_repo import BaseStockRepo
from app.clients.publisher import EventPublisher


class StockService:
    """Бизнес-логика контекста «Управление остатками».

    KeyError   — объект не найден;
    ValueError — нарушено бизнес-правило.
    """

    def __init__(self, stock_repo: BaseStockRepo, publisher: EventPublisher | None = None) -> None:
        self.stock_repo = stock_repo
        self.publisher = publisher

    def get_stocks(self, store_id: UUID | None = None) -> list[Stock]:
        return self.stock_repo.get_stocks(store_id)

    def get_stock(self, part_id: UUID) -> Stock:
        return self.stock_repo.get_stock(part_id)

    def set_stock(self, part_id: UUID, store_id: UUID, price: Decimal, quantity: int) -> Stock:
        """Команда «Обновить остаток» (продавец)."""
        reserved = 0
        try:
            current = self.stock_repo.get_stock(part_id)
        except KeyError:
            current = None
        if current is not None:
            if current.store_id != store_id:
                raise ValueError('Остаток принадлежит другому магазину')
            reserved = current.reserved
        if quantity < reserved:
            raise ValueError(f'Нельзя установить остаток меньше резерва ({reserved})')
        stock = Stock(part_id=part_id, store_id=store_id, price=price,
                      quantity=quantity, reserved=reserved)
        return self.stock_repo.save_stock(stock)

    def get_reservations(self, order_id: UUID | None = None) -> list[Reservation]:
        return self.stock_repo.get_reservations(order_id)

    def reserve(self, order_id: UUID, items: list[ReserveItem]) -> list[Reservation]:
        """Команда «Зарезервировать товар». Резервирует всё или ничего."""
        if self.stock_repo.get_reservations(order_id):
            raise ValueError(f'Для заказа {order_id} резерв уже создан')

        needed = self._merge_items(items)
        # сначала проверяем все позиции, и только потом что-то меняем
        stocks = {part_id: self._get_stock_for_reserve(part_id, qty)
                  for part_id, qty in needed.items()}

        reservations = []
        for part_id, qty in needed.items():
            stock = stocks[part_id]
            stock.reserved += qty
            self.stock_repo.save_stock(stock)
            reservations.append(self.stock_repo.create_reservation(
                Reservation(id=uuid4(), order_id=order_id, part_id=part_id, quantity=qty)))
        return reservations

    def release(self, order_id: UUID) -> list[Reservation]:
        """Команда «Снять резерв» (после отмены заказа)."""
        reservations = self.stock_repo.get_reservations(order_id)
        if not reservations:
            raise KeyError(order_id)
        released = []
        for reservation in reservations:
            if reservation.status != ReservationStatuses.ACTIVE:
                continue
            stock = self.stock_repo.get_stock(reservation.part_id)
            stock.reserved = max(stock.reserved - reservation.quantity, 0)
            self.stock_repo.save_stock(stock)
            reservation.status = ReservationStatuses.RELEASED
            released.append(self.stock_repo.save_reservation(reservation))
        return released

    # --- обработчики событий из брокера (бизнес-правила / policy) ---

    def handle_order_created(self, payload: dict) -> None:
        """Политика: «Заказ создан» -> «Зарезервировать товар»."""
        order_id = UUID(str(payload['order_id']))
        items = [ReserveItem.model_validate(i) for i in payload['items']]
        try:
            self.reserve(order_id, items)
        except ValueError as e:
            self._publish('inventory.reserve_failed', {'order_id': str(order_id), 'reason': str(e)})
        else:
            self._publish('inventory.reserved', {'order_id': str(order_id)})

    def handle_order_canceled(self, payload: dict) -> None:
        """Политика: «Заказ отменён» -> «Снять резерв»."""
        try:
            self.release(UUID(str(payload['order_id'])))
        except KeyError:
            pass  # резерва не было (например, резервирование не удалось) — снимать нечего

    # --- вложенные вспомогательные функции ---

    @staticmethod
    def _merge_items(items: list[ReserveItem]) -> dict[UUID, int]:
        needed: dict[UUID, int] = defaultdict(int)
        for item in items:
            needed[item.part_id] += item.quantity
        return dict(needed)

    def _get_stock_for_reserve(self, part_id: UUID, quantity: int) -> Stock:
        try:
            stock = self.stock_repo.get_stock(part_id)
        except KeyError:
            raise ValueError(f'Запчасть {part_id} отсутствует на складе')
        if stock.available < quantity:
            raise ValueError(f'Недостаточно запчасти {part_id}: доступно {stock.available}, '
                             f'требуется {quantity}')
        return stock

    def _publish(self, routing_key: str, payload: dict) -> None:
        if self.publisher is not None:
            self.publisher.publish(routing_key, payload)
