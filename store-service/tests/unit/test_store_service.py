# /tests/unit/test_store_service.py
from uuid import uuid4, UUID

import pytest

from app.models.store import StoreStatuses
from app.repositories.local_store_repo import LocalStoreRepo
from app.services.store_service import StoreService
from tests.unit.fakes import FakePublisher


@pytest.fixture()
def publisher() -> FakePublisher:
    return FakePublisher()


@pytest.fixture()
def service(publisher: FakePublisher) -> StoreService:
    return StoreService(LocalStoreRepo(), publisher)


@pytest.fixture()
def owner_id() -> UUID:
    return uuid4()


def test_empty_stores(service: StoreService) -> None:
    assert service.get_stores() == []


def test_create_store(service: StoreService, publisher: FakePublisher, owner_id: UUID) -> None:
    store = service.create_store(owner_id, 'АвтоМир')
    assert store.status == StoreStatuses.PENDING
    assert service.get_store(store.id) == store
    assert publisher.events == [('store.created', {'store_id': str(store.id),
                                                   'owner_id': str(owner_id)})]


def test_create_duplicate_name_same_owner(service: StoreService, owner_id: UUID) -> None:
    service.create_store(owner_id, 'АвтоМир')
    with pytest.raises(ValueError):
        service.create_store(owner_id, 'АвтоМир')


def test_same_name_other_owner_allowed(service: StoreService, owner_id: UUID) -> None:
    service.create_store(owner_id, 'АвтоМир')
    assert service.create_store(uuid4(), 'АвтоМир').name == 'АвтоМир'


def test_get_store_not_found(service: StoreService) -> None:
    with pytest.raises(KeyError):
        service.get_store(uuid4())


def test_verify_store(service: StoreService, publisher: FakePublisher, owner_id: UUID) -> None:
    store = service.create_store(owner_id, 'АвтоМир')
    verified = service.verify_store(store.id)
    assert verified.status == StoreStatuses.VERIFIED
    assert service.get_store(store.id).status == StoreStatuses.VERIFIED
    assert publisher.keys() == ['store.created', 'store.verified']


def test_verify_twice_forbidden(service: StoreService, owner_id: UUID) -> None:
    store = service.create_store(owner_id, 'АвтоМир')
    service.verify_store(store.id)
    with pytest.raises(ValueError):
        service.verify_store(store.id)


def test_verify_unknown_store(service: StoreService) -> None:
    with pytest.raises(KeyError):
        service.verify_store(uuid4())


def test_block_verified_store(service: StoreService, publisher: FakePublisher,
                              owner_id: UUID) -> None:
    store = service.create_store(owner_id, 'АвтоМир')
    service.verify_store(store.id)
    assert service.block_store(store.id).status == StoreStatuses.BLOCKED
    assert publisher.events[-1] == ('store.blocked', {'store_id': str(store.id)})


def test_block_pending_store(service: StoreService, owner_id: UUID) -> None:
    store = service.create_store(owner_id, 'АвтоМир')
    assert service.block_store(store.id).status == StoreStatuses.BLOCKED


def test_blocked_store_cannot_be_verified(service: StoreService, owner_id: UUID) -> None:
    store = service.create_store(owner_id, 'АвтоМир')
    service.block_store(store.id)
    with pytest.raises(ValueError):
        service.verify_store(store.id)


def test_block_twice_forbidden(service: StoreService, owner_id: UUID) -> None:
    store = service.create_store(owner_id, 'АвтоМир')
    service.block_store(store.id)
    with pytest.raises(ValueError):
        service.block_store(store.id)


def test_filter_and_pagination(service: StoreService, owner_id: UUID) -> None:
    mine = [service.create_store(owner_id, f'Магазин {i}') for i in range(3)]
    service.create_store(uuid4(), 'Чужой')
    service.verify_store(mine[0].id)
    assert len(service.get_stores()) == 4
    assert [s.id for s in service.get_stores(owner_id=owner_id)] == [s.id for s in mine]
    assert [s.id for s in service.get_stores(owner_id=owner_id, offset=1, count=1)] == [mine[1].id]
    assert [s.id for s in service.get_stores(status=StoreStatuses.VERIFIED)] == [mine[0].id]
