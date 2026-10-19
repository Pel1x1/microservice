from app.clients.publisher import EventPublisher


class FakePublisher(EventPublisher):
    """Мок брокера: запоминает опубликованные события вместо отправки в RabbitMQ."""

    def __init__(self) -> None:
        self.events: list[tuple[str, dict]] = []

    def publish(self, routing_key: str, payload: dict) -> None:
        self.events.append((routing_key, payload))
