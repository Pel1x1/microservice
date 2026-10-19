from uuid import UUID
from decimal import Decimal

from app.clients.publisher import EventPublisher
from app.clients.inventory_client import InventoryClient, StockInfo


class FakePublisher(EventPublisher):
    """Мок брокера: запоминает события вместо отправки в RabbitMQ."""

    def __init__(self) -> None:
        self.events: list[tuple[str, dict]] = []

    def publish(self, routing_key: str, payload: dict) -> None:
        self.events.append((routing_key, payload))

    def keys(self) -> list[str]:
        return [key for key, _ in self.events]


class FakeInventoryClient(InventoryClient):
    """Мок inventory-service: остатки задаются словарём в тесте."""

    def __init__(self) -> None:
        self.stocks: dict[UUID, StockInfo] = {}
        self.available = True

    def add(self, part_id: UUID, price: str, available: int) -> None:
        self.stocks[part_id] = StockInfo(part_id=part_id, price=Decimal(price), available=available)

    def get_stock(self, part_id: UUID) -> StockInfo:
        if not self.available:
            raise ConnectionError('inventory-service is unavailable')
        if part_id not in self.stocks:
            raise KeyError(part_id)
        return self.stocks[part_id]
