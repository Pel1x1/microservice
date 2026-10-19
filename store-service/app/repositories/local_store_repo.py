from uuid import UUID

from app.models.store import Store, StoreStatuses
from app.repositories.base_store_repo import BaseStoreRepo


class LocalStoreRepo(BaseStoreRepo):
    def __init__(self) -> None:
        self._stores: dict[UUID, Store] = {}

    def get_stores(self, status: StoreStatuses | None = None, owner_id: UUID | None = None,
                   offset: int = 0, count: int | None = None) -> list[Store]:
        stores = sorted(self._stores.values(), key=lambda s: s.created_at)
        stores = [s.model_copy() for s in stores
                  if (status is None or s.status == status)
                  and (owner_id is None or s.owner_id == owner_id)]
        end = None if count is None else offset + count
        return stores[offset:end]

    def get_store(self, store_id: UUID) -> Store:
        if store_id not in self._stores:
            raise KeyError(store_id)
        return self._stores[store_id].model_copy()

    def create_store(self, store: Store) -> Store:
        if store.id in self._stores:
            raise KeyError(store.id)
        self._stores[store.id] = store.model_copy()
        return store

    def save_store(self, store: Store) -> Store:
        if store.id not in self._stores:
            raise KeyError(store.id)
        self._stores[store.id] = store.model_copy()
        return store
