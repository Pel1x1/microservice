# /tests/unit/test_catalog_service.py
from uuid import uuid4, UUID

import pytest

from app.models.part import PartStatuses
from app.repositories.local_catalog_repo import LocalCatalogRepo
from app.services.catalog_service import CatalogService
from tests.unit.fakes import FakePublisher, FakeStoreClient


@pytest.fixture()
def stores() -> FakeStoreClient:
    return FakeStoreClient()


@pytest.fixture()
def publisher() -> FakePublisher:
    return FakePublisher()


@pytest.fixture()
def service(stores: FakeStoreClient, publisher: FakePublisher) -> CatalogService:
    # Dependency injection: локальный репозиторий, моки store-service и RabbitMQ
    return CatalogService(LocalCatalogRepo(), stores, publisher)


@pytest.fixture()
def store_id(stores: FakeStoreClient) -> UUID:
    store_id = uuid4()
    stores.add(store_id, 'verified')
    return store_id


def publish(service: CatalogService, store_id: UUID, name: str = 'Колодки тормозные',
            category: str = 'Тормоза', cars=None):
    return service.publish_part(store_id, name, category, 'Brembo', cars or ['Toyota Camry 2018'])


def test_empty_catalog(service: CatalogService) -> None:
    assert service.search_parts() == []


def test_publish_part(service: CatalogService, publisher: FakePublisher, store_id: UUID) -> None:
    part = publish(service, store_id)
    assert part.status == PartStatuses.PUBLISHED
    assert service.get_part(part.id) == part
    assert publisher.events == [('catalog.part_published',
                                 {'part_id': str(part.id), 'store_id': str(store_id)})]


def test_publish_unknown_store(service: CatalogService, publisher: FakePublisher) -> None:
    with pytest.raises(ValueError):
        publish(service, uuid4())
    assert service.search_parts() == []
    assert publisher.events == []


@pytest.mark.parametrize('status', ['pending', 'blocked'])
def test_publish_not_verified_store(service: CatalogService, stores: FakeStoreClient,
                                    status: str) -> None:
    store_id = uuid4()
    stores.add(store_id, status)
    with pytest.raises(ValueError):
        publish(service, store_id)


def test_publish_store_unavailable(service: CatalogService, stores: FakeStoreClient,
                                   store_id: UUID) -> None:
    stores.available = False
    with pytest.raises(ConnectionError):
        publish(service, store_id)


def test_get_part_not_found(service: CatalogService) -> None:
    with pytest.raises(KeyError):
        service.get_part(uuid4())


def test_unpublish_part(service: CatalogService, publisher: FakePublisher, store_id: UUID) -> None:
    part = publish(service, store_id)
    assert service.unpublish_part(part.id).status == PartStatuses.UNPUBLISHED
    assert service.search_parts() == []                       # в поиске её больше нет
    assert service.get_part(part.id).status == PartStatuses.UNPUBLISHED
    assert publisher.events[-1][0] == 'catalog.part_unpublished'


def test_unpublish_twice_forbidden(service: CatalogService, store_id: UUID) -> None:
    part = publish(service, store_id)
    service.unpublish_part(part.id)
    with pytest.raises(ValueError):
        service.unpublish_part(part.id)


def test_unpublish_unknown_part(service: CatalogService) -> None:
    with pytest.raises(KeyError):
        service.unpublish_part(uuid4())


def test_search_by_name_and_category(service: CatalogService, store_id: UUID) -> None:
    pads = publish(service, store_id, 'Колодки тормозные', 'Тормоза')
    publish(service, store_id, 'Фильтр масляный', 'Фильтры')
    assert [p.id for p in service.search_parts(query='колодки')] == [pads.id]
    assert [p.id for p in service.search_parts(category='Тормоза')] == [pads.id]
    assert len(service.search_parts()) == 2


def test_search_by_car_compatibility(service: CatalogService, store_id: UUID) -> None:
    camry = publish(service, store_id, 'Колодки A', cars=['Toyota Camry 2018'])
    publish(service, store_id, 'Колодки B', cars=['Kia Rio 2020'])
    both = publish(service, store_id, 'Колодки C', cars=['Kia Rio 2020', 'toyota camry 2018'])
    assert [p.id for p in service.search_parts(car='TOYOTA CAMRY 2018')] == [camry.id, both.id]
    assert service.search_parts(car='Lada Vesta') == []


def test_search_pagination_and_store_filter(service: CatalogService, stores: FakeStoreClient,
                                            store_id: UUID) -> None:
    other = uuid4()
    stores.add(other)
    mine = [publish(service, store_id, f'Деталь {i}') for i in range(3)]
    publish(service, other, 'Чужая деталь')
    assert [p.id for p in service.search_parts(store_id=store_id, offset=1, count=1)] == [mine[1].id]
    assert len(service.search_parts()) == 4


def test_store_blocked_unpublishes_all_its_parts(service: CatalogService, stores: FakeStoreClient,
                                                 store_id: UUID) -> None:
    other = uuid4()
    stores.add(other)
    mine = [publish(service, store_id, f'Деталь {i}') for i in range(2)]
    foreign = publish(service, other, 'Чужая деталь')
    service.handle_store_blocked({'store_id': str(store_id)})
    assert all(service.get_part(p.id).status == PartStatuses.UNPUBLISHED for p in mine)
    assert service.get_part(foreign.id).status == PartStatuses.PUBLISHED
