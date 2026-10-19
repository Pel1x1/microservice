# /tests/unit/test_stock_service.py
from uuid import uuid4, UUID
from decimal import Decimal

import pytest

from app.models.stock import ReserveItem, ReservationStatuses
from app.repositories.local_stock_repo import LocalStockRepo
from app.services.stock_service import StockService
from tests.unit.fakes import FakePublisher


@pytest.fixture()
def publisher() -> FakePublisher:
    return FakePublisher()


@pytest.fixture()
def service(publisher: FakePublisher) -> StockService:
    # Dependency injection: вместо репозитория БД — локальный, вместо RabbitMQ — мок
    return StockService(LocalStockRepo(), publisher)


@pytest.fixture()
def store_id() -> UUID:
    return uuid4()


@pytest.fixture()
def brake_pads(service: StockService, store_id: UUID) -> UUID:
    part_id = uuid4()
    service.set_stock(part_id, store_id, Decimal('2500.00'), 10)
    return part_id


@pytest.fixture()
def oil_filter(service: StockService, store_id: UUID) -> UUID:
    part_id = uuid4()
    service.set_stock(part_id, store_id, Decimal('600.00'), 2)
    return part_id


def test_empty_stocks(service: StockService) -> None:
    assert service.get_stocks() == []


def test_set_stock_creates(service: StockService, store_id: UUID) -> None:
    part_id = uuid4()
    stock = service.set_stock(part_id, store_id, Decimal('100.00'), 5)
    assert stock.quantity == 5 and stock.reserved == 0
    assert service.get_stock(part_id) == stock


def test_set_stock_updates(service: StockService, store_id: UUID, brake_pads: UUID) -> None:
    service.set_stock(brake_pads, store_id, Decimal('2700.00'), 20)
    stock = service.get_stock(brake_pads)
    assert stock.quantity == 20
    assert stock.price == Decimal('2700.00')


def test_set_stock_other_store_forbidden(service: StockService, brake_pads: UUID) -> None:
    with pytest.raises(ValueError):
        service.set_stock(brake_pads, uuid4(), Decimal('1.00'), 1)


def test_get_stocks_filter_by_store(service: StockService, store_id: UUID,
                                    brake_pads: UUID) -> None:
    service.set_stock(uuid4(), uuid4(), Decimal('10.00'), 1)  # чужой магазин
    stocks = service.get_stocks(store_id)
    assert [s.part_id for s in stocks] == [brake_pads]


def test_get_stock_not_found(service: StockService) -> None:
    with pytest.raises(KeyError):
        service.get_stock(uuid4())


def test_reserve_success(service: StockService, brake_pads: UUID, oil_filter: UUID) -> None:
    order_id = uuid4()
    reservations = service.reserve(order_id, [ReserveItem(part_id=brake_pads, quantity=4),
                                              ReserveItem(part_id=oil_filter, quantity=2)])
    assert len(reservations) == 2
    assert service.get_stock(brake_pads).available == 6
    assert service.get_stock(oil_filter).available == 0
    assert len(service.get_reservations(order_id)) == 2


def test_reserve_merges_same_part(service: StockService, brake_pads: UUID) -> None:
    order_id = uuid4()
    reservations = service.reserve(order_id, [ReserveItem(part_id=brake_pads, quantity=1),
                                              ReserveItem(part_id=brake_pads, quantity=2)])
    assert len(reservations) == 1
    assert reservations[0].quantity == 3


def test_reserve_not_enough_changes_nothing(service: StockService, brake_pads: UUID,
                                            oil_filter: UUID) -> None:
    with pytest.raises(ValueError):
        service.reserve(uuid4(), [ReserveItem(part_id=brake_pads, quantity=1),
                                  ReserveItem(part_id=oil_filter, quantity=3)])
    # «всё или ничего»: первая позиция тоже не должна быть зарезервирована
    assert service.get_stock(brake_pads).reserved == 0
    assert service.get_reservations() == []


def test_reserve_unknown_part(service: StockService) -> None:
    with pytest.raises(ValueError):
        service.reserve(uuid4(), [ReserveItem(part_id=uuid4(), quantity=1)])


def test_reserve_repeat_forbidden(service: StockService, brake_pads: UUID) -> None:
    order_id = uuid4()
    service.reserve(order_id, [ReserveItem(part_id=brake_pads, quantity=1)])
    with pytest.raises(ValueError):
        service.reserve(order_id, [ReserveItem(part_id=brake_pads, quantity=1)])


def test_quantity_below_reserved_forbidden(service: StockService, store_id: UUID,
                                           brake_pads: UUID) -> None:
    service.reserve(uuid4(), [ReserveItem(part_id=brake_pads, quantity=5)])
    with pytest.raises(ValueError):
        service.set_stock(brake_pads, store_id, Decimal('2500.00'), 4)


def test_release(service: StockService, brake_pads: UUID) -> None:
    order_id = uuid4()
    service.reserve(order_id, [ReserveItem(part_id=brake_pads, quantity=5)])
    released = service.release(order_id)
    assert [r.status for r in released] == [ReservationStatuses.RELEASED]
    assert service.get_stock(brake_pads).reserved == 0
    # повторное снятие резерва ничего не меняет
    assert service.release(order_id) == []


def test_release_unknown_order(service: StockService) -> None:
    with pytest.raises(KeyError):
        service.release(uuid4())


def test_handle_order_created_publishes_reserved(service: StockService, publisher: FakePublisher,
                                                 brake_pads: UUID) -> None:
    order_id = uuid4()
    service.handle_order_created({'order_id': str(order_id),
                                  'items': [{'part_id': str(brake_pads), 'quantity': 2}]})
    assert publisher.events == [('inventory.reserved', {'order_id': str(order_id)})]
    assert service.get_stock(brake_pads).reserved == 2


def test_handle_order_created_publishes_failure(service: StockService, publisher: FakePublisher,
                                                oil_filter: UUID) -> None:
    order_id = uuid4()
    service.handle_order_created({'order_id': str(order_id),
                                  'items': [{'part_id': str(oil_filter), 'quantity': 100}]})
    routing_key, payload = publisher.events[0]
    assert routing_key == 'inventory.reserve_failed'
    assert payload['order_id'] == str(order_id)


def test_handle_order_canceled_releases(service: StockService, brake_pads: UUID) -> None:
    order_id = uuid4()
    service.reserve(order_id, [ReserveItem(part_id=brake_pads, quantity=3)])
    service.handle_order_canceled({'order_id': str(order_id)})
    assert service.get_stock(brake_pads).reserved == 0


def test_handle_order_canceled_without_reserve(service: StockService) -> None:
    service.handle_order_canceled({'order_id': str(uuid4())})  # не должно падать
