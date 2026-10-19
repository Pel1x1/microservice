from uuid import UUID, uuid4
from datetime import datetime, timezone

from app.models.part import Part, PartStatuses
from app.repositories.base_catalog_repo import BaseCatalogRepo
from app.clients.store_client import StoreClient
from app.clients.publisher import EventPublisher


class CatalogService:
    """Бизнес-логика контекста «Управление каталогом».

    KeyError        — запчасть не найдена;
    ValueError      — нарушено бизнес-правило (магазин не верифицирован, повторное снятие);
    ConnectionError — недоступен store-service.
    """

    def __init__(self, part_repo: BaseCatalogRepo, store_client: StoreClient,
                 publisher: EventPublisher | None = None) -> None:
        self.part_repo = part_repo
        self.store_client = store_client
        self.publisher = publisher

    def search_parts(self, query: str | None = None, category: str | None = None,
                     car: str | None = None, store_id: UUID | None = None,
                     offset: int = 0, count: int | None = None) -> list[Part]:
        """Поиск по каталогу: только опубликованные карточки."""
        return self.part_repo.get_parts(query, category, car, store_id, PartStatuses.PUBLISHED,
                                        offset, count)

    def get_part(self, part_id: UUID) -> Part:
        return self.part_repo.get_part(part_id)

    def publish_part(self, store_id: UUID, name: str, category: str, brand: str,
                     compatible_cars: list[str]) -> Part:
        """Команда «Опубликовать запчасть» (продавец)."""
        self._check_store(store_id)  # вложенный синхронный вызов store-service
        part = Part(id=uuid4(), store_id=store_id, name=name, category=category, brand=brand,
                    compatible_cars=compatible_cars, status=PartStatuses.PUBLISHED,
                    created_at=datetime.now(timezone.utc))
        self.part_repo.create_part(part)
        self._publish('catalog.part_published', {'part_id': str(part.id), 'store_id': str(store_id)})
        return part

    def unpublish_part(self, part_id: UUID) -> Part:
        """Команда «Снять запчасть с публикации» (продавец)."""
        part = self.part_repo.get_part(part_id)
        if part.status == PartStatuses.UNPUBLISHED:
            raise ValueError('Запчасть уже снята с публикации')
        part.status = PartStatuses.UNPUBLISHED
        self.part_repo.save_part(part)
        self._publish('catalog.part_unpublished', {'part_id': str(part.id)})
        return part

    # --- обработчики событий из брокера (policy) ---

    def handle_store_blocked(self, payload: dict) -> None:
        """Политика: «Магазин заблокирован» -> снять с публикации все его запчасти."""
        store_id = UUID(str(payload['store_id']))
        for part in self.part_repo.get_parts(store_id=store_id, status=PartStatuses.PUBLISHED):
            part.status = PartStatuses.UNPUBLISHED
            self.part_repo.save_part(part)

    # --- вложенные вспомогательные функции ---

    def _check_store(self, store_id: UUID) -> None:
        try:
            store = self.store_client.get_store(store_id)
        except KeyError:
            raise ValueError(f'Магазин {store_id} не найден')
        if store.status != 'verified':
            raise ValueError(f'Магазин {store_id} не верифицирован (статус: {store.status})')

    def _publish(self, routing_key: str, payload: dict) -> None:
        if self.publisher is not None:
            self.publisher.publish(routing_key, payload)
