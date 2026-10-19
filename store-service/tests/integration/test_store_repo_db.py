# /tests/integration/test_store_repo_db.py
from uuid import uuid4
from datetime import datetime, timezone, timedelta

import pytest
from sqlalchemy.orm import Session

from app.models.store import Store, StoreStatuses
from app.repositories.db_store_repo import DbStoreRepo
from app.services.store_service import StoreService


@pytest.fixture()
def repo(db: Session) -> DbStoreRepo:
    return DbStoreRepo(db)


def new_store(owner_id=None, minutes: int = 0) -> Store:
    return Store(id=uuid4(), owner_id=owner_id or uuid4(), name='АвтоМир',
                 created_at=datetime(2026, 10, 1, tzinfo=timezone.utc) + timedelta(minutes=minutes))


def test_empty_list(repo: DbStoreRepo) -> None:
    assert repo.get_stores() == []


def test_create_and_get(repo: DbStoreRepo) -> None:
    store = new_store()
    assert repo.create_store(store) == store
    assert repo.get_store(store.id) == store


def test_create_repeat(repo: DbStoreRepo) -> None:
    store = new_store()
    repo.create_store(store)
    with pytest.raises(KeyError):
        repo.create_store(store)


def test_get_not_found(repo: DbStoreRepo) -> None:
    with pytest.raises(KeyError):
        repo.get_store(uuid4())


def test_save_store(repo: DbStoreRepo) -> None:
    store = new_store()
    repo.create_store(store)
    store.status = StoreStatuses.VERIFIED
    repo.save_store(store)
    assert repo.get_store(store.id).status == StoreStatuses.VERIFIED


def test_save_unknown_store(repo: DbStoreRepo) -> None:
    with pytest.raises(KeyError):
        repo.save_store(new_store())


def test_filters_sorting_pagination(repo: DbStoreRepo) -> None:
    owner_id = uuid4()
    third, first, second = new_store(owner_id, 30), new_store(owner_id, 10), new_store(owner_id, 20)
    for store in (third, first, second, new_store(minutes=40)):
        repo.create_store(store)
    second.status = StoreStatuses.BLOCKED
    repo.save_store(second)
    assert [s.id for s in repo.get_stores(owner_id=owner_id)] == [first.id, second.id, third.id]
    assert [s.id for s in repo.get_stores(owner_id=owner_id, offset=1, count=1)] == [second.id]
    assert [s.id for s in repo.get_stores(status=StoreStatuses.BLOCKED)] == [second.id]
    assert len(repo.get_stores()) == 4


def test_service_verify_with_db(repo: DbStoreRepo) -> None:
    """Бизнес-логика поверх настоящей БД."""
    service = StoreService(repo)
    store = service.create_store(uuid4(), 'АвтоМир')
    service.verify_store(store.id)
    assert repo.get_store(store.id).status == StoreStatuses.VERIFIED
