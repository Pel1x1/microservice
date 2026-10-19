# /tests/integration/test_catalog_repo_db.py
from uuid import uuid4
from datetime import datetime, timezone, timedelta

import pytest
from sqlalchemy.orm import Session

from app.models.part import Part, PartStatuses
from app.repositories.db_catalog_repo import DbCatalogRepo
from app.services.catalog_service import CatalogService
from tests.unit.fakes import FakeStoreClient


@pytest.fixture()
def repo(db: Session) -> DbCatalogRepo:
    return DbCatalogRepo(db)


def new_part(name='Колодки тормозные', category='Тормоза', cars=None, store_id=None,
             minutes: int = 0) -> Part:
    return Part(id=uuid4(), store_id=store_id or uuid4(), name=name, category=category,
                brand='Brembo', compatible_cars=cars or ['Toyota Camry 2018'],
                created_at=datetime(2026, 10, 1, tzinfo=timezone.utc) + timedelta(minutes=minutes))


def test_empty_list(repo: DbCatalogRepo) -> None:
    assert repo.get_parts() == []


def test_create_and_get(repo: DbCatalogRepo) -> None:
    part = new_part(cars=['Toyota Camry 2018', 'Kia Rio 2020'])
    assert repo.create_part(part) == part
    assert repo.get_part(part.id) == part       # список совместимости (JSON) восстановлен


def test_create_repeat(repo: DbCatalogRepo) -> None:
    part = new_part()
    repo.create_part(part)
    with pytest.raises(KeyError):
        repo.create_part(part)


def test_get_not_found(repo: DbCatalogRepo) -> None:
    with pytest.raises(KeyError):
        repo.get_part(uuid4())


def test_save_part(repo: DbCatalogRepo) -> None:
    part = new_part()
    repo.create_part(part)
    part.status = PartStatuses.UNPUBLISHED
    part.compatible_cars = ['Lada Vesta 2021']
    repo.save_part(part)
    saved = repo.get_part(part.id)
    assert saved.status == PartStatuses.UNPUBLISHED
    assert saved.compatible_cars == ['Lada Vesta 2021']


def test_save_unknown_part(repo: DbCatalogRepo) -> None:
    with pytest.raises(KeyError):
        repo.save_part(new_part())


def test_search_filters(repo: DbCatalogRepo) -> None:
    pads = new_part('Колодки тормозные', 'Тормоза', ['Toyota Camry 2018'], minutes=1)
    oil = new_part('Фильтр масляный', 'Фильтры', ['Kia Rio 2020'], minutes=2)
    both = new_part('Колодки задние', 'Тормоза', ['Kia Rio 2020', 'Toyota Camry 2018'], minutes=3)
    for part in (both, oil, pads):
        repo.create_part(part)
    assert [p.id for p in repo.get_parts()] == [pads.id, oil.id, both.id]
    assert [p.id for p in repo.get_parts(query='колодки')] == [pads.id, both.id]
    assert [p.id for p in repo.get_parts(category='Фильтры')] == [oil.id]
    assert [p.id for p in repo.get_parts(car='toyota camry 2018')] == [pads.id, both.id]
    assert [p.id for p in repo.get_parts(offset=1, count=1)] == [oil.id]


def test_filter_by_store_and_status(repo: DbCatalogRepo) -> None:
    store_id = uuid4()
    mine, other = new_part(store_id=store_id), new_part()
    for part in (mine, other):
        repo.create_part(part)
    mine.status = PartStatuses.UNPUBLISHED
    repo.save_part(mine)
    assert [p.id for p in repo.get_parts(store_id=store_id)] == [mine.id]
    assert [p.id for p in repo.get_parts(status=PartStatuses.PUBLISHED)] == [other.id]


def test_service_publish_and_store_blocked_with_db(repo: DbCatalogRepo) -> None:
    """Бизнес-логика поверх настоящей БД (store-service замокан)."""
    stores = FakeStoreClient()
    store_id = uuid4()
    stores.add(store_id)
    service = CatalogService(repo, stores)
    part = service.publish_part(store_id, 'Колодки', 'Тормоза', 'Brembo', ['Kia Rio 2020'])
    service.handle_store_blocked({'store_id': str(store_id)})
    assert repo.get_part(part.id).status == PartStatuses.UNPUBLISHED
