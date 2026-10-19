from uuid import UUID

from app.models.part import Part, PartStatuses
from app.repositories.base_catalog_repo import BaseCatalogRepo


class LocalCatalogRepo(BaseCatalogRepo):
    def __init__(self) -> None:
        self._parts: dict[UUID, Part] = {}

    def get_parts(self, query: str | None = None, category: str | None = None,
                  car: str | None = None, store_id: UUID | None = None,
                  status: PartStatuses | None = None, offset: int = 0,
                  count: int | None = None) -> list[Part]:
        parts = sorted(self._parts.values(), key=lambda p: p.created_at)
        parts = [p.model_copy() for p in parts
                 if (query is None or query.lower() in p.name.lower())
                 and (category is None or p.category == category)
                 and (car is None or car.lower() in [c.lower() for c in p.compatible_cars])
                 and (store_id is None or p.store_id == store_id)
                 and (status is None or p.status == status)]
        end = None if count is None else offset + count
        return parts[offset:end]

    def get_part(self, part_id: UUID) -> Part:
        if part_id not in self._parts:
            raise KeyError(part_id)
        return self._parts[part_id].model_copy()

    def create_part(self, part: Part) -> Part:
        if part.id in self._parts:
            raise KeyError(part.id)
        self._parts[part.id] = part.model_copy()
        return part

    def save_part(self, part: Part) -> Part:
        if part.id not in self._parts:
            raise KeyError(part.id)
        self._parts[part.id] = part.model_copy()
        return part
