from abc import ABC, abstractmethod
from uuid import UUID

from app.models.store import Store, StoreStatuses


class BaseStoreRepo(ABC):
    @abstractmethod
    def get_stores(self, status: StoreStatuses | None = None, owner_id: UUID | None = None,
                   offset: int = 0, count: int | None = None) -> list[Store]:
        """Список магазинов, отсортированный по дате создания."""

    @abstractmethod
    def get_store(self, store_id: UUID) -> Store:
        """KeyError, если магазина нет."""

    @abstractmethod
    def create_store(self, store: Store) -> Store:
        """KeyError, если магазин с таким id уже есть."""

    @abstractmethod
    def save_store(self, store: Store) -> Store:
        """KeyError, если магазина нет."""
