# /tests/unit/test_order_service.py
from uuid import uuid4, UUID
from decimal import Decimal

import pytest

from app.models.order import OrderStatuses, CreateOrderItem
from app.repositories.local_order_repo import LocalOrderRepo
from app.services.order_service import OrderService
from tests.unit.fakes import FakePublisher, FakeInventoryClient


@pytest.fixture()
def inventory() -> FakeInventoryClient:
    return FakeInventoryClient()


@pytest.fixture()
def publisher() -> FakePublisher:
    return FakePublisher()


@pytest.fixture()
def service(inventory: FakeInventoryClient, publisher: FakePublisher) -> OrderService:
    # Dependency injection: локальный репозиторий + моки inventory-service и RabbitMQ
    return OrderService(LocalOrderRepo(), inventory, publisher)


@pytest.fixture()
def brake_pads(inventory: FakeInventoryClient) -> UUID:
    part_id = uuid4()
    inventory.add(part_id, '2500.00', available=10)
    return part_id


@pytest.fixture()
def oil_filter(inventory: FakeInventoryClient) -> UUID:
    part_id = uuid4()
    inventory.add(part_id, '600.00', available=1)
    return part_id


@pytest.fixture()
def customer_id() -> UUID:
    return uuid4()


def make_order(service: OrderService, customer_id: UUID, part_id: UUID, qty: int = 1):
    return service.create_order(customer_id, 'Москва, пр. Вернадского, 78',
                                [CreateOrderItem(part_id=part_id, quantity=qty)])


def test_empty_orders(service: OrderService) -> None:
    assert service.get_orders() == []


def test_create_order(service: OrderService, publisher: FakePublisher, customer_id: UUID,
                      brake_pads: UUID, oil_filter: UUID) -> None:
    order = service.create_order(customer_id, 'Москва', [
        CreateOrderItem(part_id=brake_pads, quantity=2),
        CreateOrderItem(part_id=oil_filter, quantity=1)])
    assert order.status == OrderStatuses.CREATED
    assert order.customer_id == customer_id
    assert order.items[0].price == Decimal('2500.00')   # цена взята из inventory-service
    assert order.total == Decimal('5600.00')
    assert service.get_order(order.id) == order

    routing_key, payload = publisher.events[0]
    assert routing_key == 'order.created'
    assert payload['order_id'] == str(order.id)
    assert payload['items'] == [{'part_id': str(brake_pads), 'quantity': 2},
                                {'part_id': str(oil_filter), 'quantity': 1}]


def test_create_order_merges_items(service: OrderService, customer_id: UUID,
                                   brake_pads: UUID) -> None:
    order = service.create_order(customer_id, 'Москва', [
        CreateOrderItem(part_id=brake_pads, quantity=1),
        CreateOrderItem(part_id=brake_pads, quantity=2)])
    assert len(order.items) == 1
    assert order.items[0].quantity == 3


def test_create_order_unknown_part(service: OrderService, publisher: FakePublisher,
                                   customer_id: UUID) -> None:
    with pytest.raises(ValueError):
        make_order(service, customer_id, uuid4())
    assert service.get_orders() == []
    assert publisher.events == []


def test_create_order_not_enough(service: OrderService, customer_id: UUID,
                                 oil_filter: UUID) -> None:
    with pytest.raises(ValueError):
        make_order(service, customer_id, oil_filter, qty=2)


def test_create_order_inventory_unavailable(service: OrderService, inventory: FakeInventoryClient,
                                            customer_id: UUID, brake_pads: UUID) -> None:
    inventory.available = False
    with pytest.raises(ConnectionError):
        make_order(service, customer_id, brake_pads)


def test_get_order_not_found(service: OrderService) -> None:
    with pytest.raises(KeyError):
        service.get_order(uuid4())


def test_full_lifecycle(service: OrderService, publisher: FakePublisher, customer_id: UUID,
                        brake_pads: UUID) -> None:
    order = make_order(service, customer_id, brake_pads)
    service.handle_payment_confirmed({'order_id': str(order.id)})
    assert service.get_order(order.id).status == OrderStatuses.CONFIRMED
    service.assemble_order(order.id)
    assert service.get_order(order.id).status == OrderStatuses.ASSEMBLED
    service.handle_delivery_delivered({'order_id': str(order.id)})
    assert service.get_order(order.id).status == OrderStatuses.COMPLETED
    assert publisher.keys() == ['order.created', 'order.assembled']


def test_assemble_unpaid_forbidden(service: OrderService, customer_id: UUID,
                                   brake_pads: UUID) -> None:
    order = make_order(service, customer_id, brake_pads)
    with pytest.raises(ValueError):
        service.assemble_order(order.id)


def test_complete_not_assembled_forbidden(service: OrderService, customer_id: UUID,
                                          brake_pads: UUID) -> None:
    order = make_order(service, customer_id, brake_pads)
    with pytest.raises(ValueError):
        service.complete_order(order.id)


def test_cancel_unpaid_order(service: OrderService, publisher: FakePublisher, customer_id: UUID,
                             brake_pads: UUID) -> None:
    order = make_order(service, customer_id, brake_pads)
    canceled = service.cancel_order(order.id, 'передумал')
    assert canceled.status == OrderStatuses.CANCELED
    routing_key, payload = publisher.events[-1]
    assert routing_key == 'order.canceled'
    assert payload == {'order_id': str(order.id), 'reason': 'передумал', 'refund_required': False}


def test_cancel_paid_order_requires_refund(service: OrderService, publisher: FakePublisher,
                                           customer_id: UUID, brake_pads: UUID) -> None:
    order = make_order(service, customer_id, brake_pads)
    service.confirm_order(order.id)
    service.cancel_order(order.id)
    assert publisher.events[-1][1]['refund_required'] is True


def test_cancel_completed_forbidden(service: OrderService, customer_id: UUID,
                                    brake_pads: UUID) -> None:
    order = make_order(service, customer_id, brake_pads)
    service.confirm_order(order.id)
    service.assemble_order(order.id)
    service.complete_order(order.id)
    with pytest.raises(ValueError):
        service.cancel_order(order.id)


def test_cancel_twice_forbidden(service: OrderService, customer_id: UUID,
                                brake_pads: UUID) -> None:
    order = make_order(service, customer_id, brake_pads)
    service.cancel_order(order.id)
    with pytest.raises(ValueError):
        service.cancel_order(order.id)


def test_reserve_failed_cancels_order(service: OrderService, customer_id: UUID,
                                      brake_pads: UUID) -> None:
    order = make_order(service, customer_id, brake_pads)
    service.handle_reserve_failed({'order_id': str(order.id), 'reason': 'нет на складе'})
    assert service.get_order(order.id).status == OrderStatuses.CANCELED


def test_filter_and_pagination(service: OrderService, customer_id: UUID,
                               brake_pads: UUID) -> None:
    mine = [make_order(service, customer_id, brake_pads) for _ in range(3)]
    make_order(service, uuid4(), brake_pads)  # заказ другого покупателя
    service.cancel_order(mine[0].id)

    assert len(service.get_orders()) == 4
    assert [o.id for o in service.get_orders(customer_id=customer_id)] == [o.id for o in mine]
    assert [o.id for o in service.get_orders(customer_id=customer_id, offset=1, count=1)] \
        == [mine[1].id]
    assert [o.id for o in service.get_orders(status=OrderStatuses.CANCELED)] == [mine[0].id]
