from abc import ABC, abstractmethod
from uuid import UUID

from app.models.part import Part, PartStatuses


class BaseCatalogRepo(ABC):
    @abstractmethod
    def get_parts(self, query: str | None = None, category: str | None = None,
                  car: str | None = None, store_id: UUID | None = None,
                  status: PartStatuses | None = None, offset: int = 0,
                  count: int | None = None) -> list[Part]:
        """Поиск: query — часть названия, car — автомобиль из списка совместимости
        (без учёта регистра). Сортировка по дате создания."""

    @abstractmethod
    def get_part(self, part_id: UUID) -> Part:
        """KeyError, если запчасти нет."""

    @abstractmethod
    def create_part(self, part: Part) -> Part:
        """KeyError, если запчасть с таким id уже есть."""

    @abstractmethod
    def save_part(self, part: Part) -> Part:
        """KeyError, если запчасти нет."""
