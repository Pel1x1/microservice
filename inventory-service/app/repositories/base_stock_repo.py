from abc import ABC, abstractmethod
from uuid import UUID

from app.models.stock import Stock, Reservation


class BaseStockRepo(ABC):
    """Интерфейс репозитория остатков. Реализации: локальная (память) и БД."""

    @abstractmethod
    def get_stocks(self, store_id: UUID | None = None) -> list[Stock]: ...

    @abstractmethod
    def get_stock(self, part_id: UUID) -> Stock:
        """KeyError, если остатка нет."""

    @abstractmethod
    def save_stock(self, stock: Stock) -> Stock:
        """Создаёт или обновляет остаток."""

    @abstractmethod
    def create_reservation(self, reservation: Reservation) -> Reservation:
        """KeyError, если резерв с таким id уже есть."""

    @abstractmethod
    def get_reservations(self, order_id: UUID | None = None) -> list[Reservation]: ...

    @abstractmethod
    def save_reservation(self, reservation: Reservation) -> Reservation:
        """KeyError, если резерва нет."""
