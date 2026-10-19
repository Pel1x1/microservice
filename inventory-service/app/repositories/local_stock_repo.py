from uuid import UUID

from app.models.stock import Stock, Reservation
from app.repositories.base_stock_repo import BaseStockRepo


class LocalStockRepo(BaseStockRepo):
    """Хранилище в памяти процесса. Используется в unit-тестах."""

    def __init__(self) -> None:
        self._stocks: dict[UUID, Stock] = {}
        self._reservations: dict[UUID, Reservation] = {}

    def get_stocks(self, store_id: UUID | None = None) -> list[Stock]:
        return [s.model_copy() for s in self._stocks.values()
                if store_id is None or s.store_id == store_id]

    def get_stock(self, part_id: UUID) -> Stock:
        if part_id not in self._stocks:
            raise KeyError(part_id)
        return self._stocks[part_id].model_copy()

    def save_stock(self, stock: Stock) -> Stock:
        self._stocks[stock.part_id] = stock.model_copy()
        return stock

    def create_reservation(self, reservation: Reservation) -> Reservation:
        if reservation.id in self._reservations:
            raise KeyError(reservation.id)
        self._reservations[reservation.id] = reservation.model_copy()
        return reservation

    def get_reservations(self, order_id: UUID | None = None) -> list[Reservation]:
        return [r.model_copy() for r in self._reservations.values()
                if order_id is None or r.order_id == order_id]

    def save_reservation(self, reservation: Reservation) -> Reservation:
        if reservation.id not in self._reservations:
            raise KeyError(reservation.id)
        self._reservations[reservation.id] = reservation.model_copy()
        return reservation
