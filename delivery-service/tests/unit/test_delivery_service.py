# /tests/unit/test_delivery_service.py
from uuid import uuid4, UUID

import pytest

from app.models.delivery import DeliveryStatuses
from app.repositories.local_delivery_repo import LocalDeliveryRepo
from app.services.delivery_service import DeliveryService
from tests.unit.fakes import FakePublisher


@pytest.fixture()
def publisher() -> FakePublisher:
    return FakePublisher()


@pytest.fixture()
def service(publisher: FakePublisher) -> DeliveryService:
    return DeliveryService(LocalDeliveryRepo(), publisher)


@pytest.fixture()
def order_id() -> UUID:
    return uuid4()


def assembled(order_id: UUID, address: str = 'Москва, пр. Вернадского, 78') -> dict:
    """Событие order.assembled, как его публикует order-service."""
    return {'order_id': str(order_id), 'address': address}


def test_empty_deliveries(service: DeliveryService) -> None:
    assert service.get_deliveries() == []


def test_order_assembled_assigns_delivery(service: DeliveryService, publisher: FakePublisher,
                                          order_id: UUID) -> None:
    service.handle_order_assembled(assembled(order_id))
    [delivery] = service.get_deliveries(order_id=order_id)
    assert delivery.status == DeliveryStatuses.ASSIGNED
    assert delivery.address == 'Москва, пр. Вернадского, 78'
    assert service.get_delivery(delivery.id) == delivery
    assert publisher.events == [('delivery.assigned', {'order_id': str(order_id),
                                                       'delivery_id': str(delivery.id)})]


def test_order_assembled_twice_is_idempotent(service: DeliveryService, publisher: FakePublisher,
                                             order_id: UUID) -> None:
    service.handle_order_assembled(assembled(order_id))
    service.handle_order_assembled(assembled(order_id))
    assert len(service.get_deliveries()) == 1
    assert len(publisher.events) == 1


def test_get_delivery_not_found(service: DeliveryService) -> None:
    with pytest.raises(KeyError):
        service.get_delivery(uuid4())


def test_full_lifecycle(service: DeliveryService, publisher: FakePublisher, order_id: UUID) -> None:
    delivery = service.assign_delivery(order_id, 'Москва')
    assert service.ship_delivery(delivery.id).status == DeliveryStatuses.IN_TRANSIT
    assert service.deliver_delivery(delivery.id).status == DeliveryStatuses.DELIVERED
    assert service.get_delivery(delivery.id).status == DeliveryStatuses.DELIVERED
    assert publisher.keys() == ['delivery.assigned', 'delivery.delivered']
    assert publisher.events[-1][1] == {'order_id': str(order_id)}


def test_deliver_before_ship_forbidden(service: DeliveryService, publisher: FakePublisher,
                                       order_id: UUID) -> None:
    delivery = service.assign_delivery(order_id, 'Москва')
    with pytest.raises(ValueError):
        service.deliver_delivery(delivery.id)
    assert 'delivery.delivered' not in publisher.keys()


def test_ship_twice_forbidden(service: DeliveryService, order_id: UUID) -> None:
    delivery = service.assign_delivery(order_id, 'Москва')
    service.ship_delivery(delivery.id)
    with pytest.raises(ValueError):
        service.ship_delivery(delivery.id)


def test_deliver_twice_forbidden(service: DeliveryService, order_id: UUID) -> None:
    delivery = service.assign_delivery(order_id, 'Москва')
    service.ship_delivery(delivery.id)
    service.deliver_delivery(delivery.id)
    with pytest.raises(ValueError):
        service.deliver_delivery(delivery.id)


def test_unknown_delivery(service: DeliveryService) -> None:
    with pytest.raises(KeyError):
        service.ship_delivery(uuid4())
    with pytest.raises(KeyError):
        service.deliver_delivery(uuid4())


def test_filter_and_pagination(service: DeliveryService) -> None:
    deliveries = [service.assign_delivery(uuid4(), f'Адрес {i}') for i in range(3)]
    assert len(service.get_deliveries()) == 3
    assert [d.id for d in service.get_deliveries(offset=1, count=1)] == [deliveries[1].id]
    assert [d.id for d in service.get_deliveries(order_id=deliveries[2].order_id)] == [deliveries[2].id]
