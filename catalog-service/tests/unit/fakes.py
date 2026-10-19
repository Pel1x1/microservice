from app.clients.publisher import EventPublisher


class FakePublisher(EventPublisher):
    """Мок брокера: запоминает опубликованные события вместо отправки в RabbitMQ."""

    def __init__(self) -> None:
        self.events: list[tuple[str, dict]] = []

    def publish(self, routing_key: str, payload: dict) -> None:
        self.events.append((routing_key, payload))

    def keys(self) -> list[str]:
        return [key for key, _ in self.events]


from uuid import UUID

from app.clients.store_client import StoreClient, StoreInfo


class FakeStoreClient(StoreClient):
    """Мок store-service: статусы магазинов задаются в тесте."""

    def __init__(self) -> None:
        self.stores: dict[UUID, StoreInfo] = {}
        self.available = True

    def add(self, store_id: UUID, status: str = 'verified') -> None:
        self.stores[store_id] = StoreInfo(id=store_id, status=status)

    def get_store(self, store_id: UUID) -> StoreInfo:
        if not self.available:
            raise ConnectionError('store-service is unavailable')
        if store_id not in self.stores:
            raise KeyError(store_id)
        return self.stores[store_id]
