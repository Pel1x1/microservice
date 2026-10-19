from uuid import UUID, uuid4
from datetime import datetime, timezone

from app.models.store import Store, StoreStatuses
from app.repositories.base_store_repo import BaseStoreRepo
from app.clients.publisher import EventPublisher


class StoreService:
    """Бизнес-логика контекста «Управление магазинами».

    KeyError   — магазин не найден;
    ValueError — нарушено бизнес-правило (недопустимый переход статуса, дубликат).
    """

    def __init__(self, store_repo: BaseStoreRepo, publisher: EventPublisher | None = None) -> None:
        self.store_repo = store_repo
        self.publisher = publisher

    def get_stores(self, status: StoreStatuses | None = None, owner_id: UUID | None = None,
                   offset: int = 0, count: int | None = None) -> list[Store]:
        return self.store_repo.get_stores(status, owner_id, offset, count)

    def get_store(self, store_id: UUID) -> Store:
        return self.store_repo.get_store(store_id)

    def create_store(self, owner_id: UUID, name: str) -> Store:
        """Команда «Создать магазин» (продавец). Магазин ждёт верификации."""
        if any(s.name == name for s in self.store_repo.get_stores(owner_id=owner_id)):
            raise ValueError(f'У продавца уже есть магазин «{name}»')
        store = Store(id=uuid4(), owner_id=owner_id, name=name, status=StoreStatuses.PENDING,
                      created_at=datetime.now(timezone.utc))
        self.store_repo.create_store(store)
        self._publish('store.created', {'store_id': str(store.id), 'owner_id': str(owner_id)})
        return store

    def verify_store(self, store_id: UUID) -> Store:
        """Команда «Верифицировать магазин» (администратор)."""
        store = self._change_status(store_id, {StoreStatuses.PENDING}, StoreStatuses.VERIFIED)
        self._publish('store.verified', {'store_id': str(store.id)})
        return store

    def block_store(self, store_id: UUID) -> Store:
        """Команда «Заблокировать магазин» (администратор)."""
        store = self._change_status(store_id, {StoreStatuses.PENDING, StoreStatuses.VERIFIED},
                                    StoreStatuses.BLOCKED)
        self._publish('store.blocked', {'store_id': str(store.id)})
        return store

    # --- вложенные вспомогательные функции ---

    def _change_status(self, store_id: UUID, allowed: set[StoreStatuses],
                       new_status: StoreStatuses) -> Store:
        store = self.store_repo.get_store(store_id)
        if store.status not in allowed:
            raise ValueError(f'Магазин в статусе {store.status.value} нельзя перевести '
                             f'в {new_status.value}')
        store.status = new_status
        return self.store_repo.save_store(store)

    def _publish(self, routing_key: str, payload: dict) -> None:
        if self.publisher is not None:
            self.publisher.publish(routing_key, payload)
