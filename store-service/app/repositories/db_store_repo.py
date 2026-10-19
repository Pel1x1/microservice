from uuid import UUID

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.store import Store, StoreStatuses
from app.repositories.base_store_repo import BaseStoreRepo
from app.schemas.store import Store as DBStore


class DbStoreRepo(BaseStoreRepo):
    def __init__(self, db: Session) -> None:
        self.db = db

    def get_stores(self, status: StoreStatuses | None = None, owner_id: UUID | None = None,
                   offset: int = 0, count: int | None = None) -> list[Store]:
        query = select(DBStore).order_by(DBStore.created_at)
        if status is not None:
            query = query.where(DBStore.status == status)
        if owner_id is not None:
            query = query.where(DBStore.owner_id == owner_id)
        query = query.offset(offset)
        if count is not None:
            query = query.limit(count)
        return [Store.model_validate(s) for s in self.db.scalars(query).all()]

    def get_store(self, store_id: UUID) -> Store:
        store = self.db.get(DBStore, store_id)
        if store is None:
            raise KeyError(store_id)
        return Store.model_validate(store)

    def create_store(self, store: Store) -> Store:
        if self.db.get(DBStore, store.id) is not None:
            raise KeyError(store.id)
        self.db.add(DBStore(**store.model_dump()))
        self.db.commit()
        return store

    def save_store(self, store: Store) -> Store:
        db_store = self.db.get(DBStore, store.id)
        if db_store is None:
            raise KeyError(store.id)
        db_store.name = store.name
        db_store.status = store.status
        self.db.commit()
        return store
