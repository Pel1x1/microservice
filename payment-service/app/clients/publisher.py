import json
import logging
from abc import ABC, abstractmethod

import pika

from app.observability import EVENTS_PUBLISHED

logger = logging.getLogger('automarket')


class EventPublisher(ABC):
    @abstractmethod
    def publish(self, routing_key: str, payload: dict) -> None: ...


class RabbitPublisher(EventPublisher):
    """Публикует доменные события в topic-обменник RabbitMQ."""

    def __init__(self, amqp_url: str, exchange: str) -> None:
        self.amqp_url = amqp_url
        self.exchange = exchange

    def publish(self, routing_key: str, payload: dict) -> None:
        connection = pika.BlockingConnection(pika.URLParameters(self.amqp_url))
        try:
            channel = connection.channel()
            channel.exchange_declare(exchange=self.exchange, exchange_type='topic', durable=True)
            channel.basic_publish(
                exchange=self.exchange,
                routing_key=routing_key,
                body=json.dumps(payload, default=str).encode(),
                properties=pika.BasicProperties(
                    content_type='application/json',
                    delivery_mode=pika.spec.PERSISTENT_DELIVERY_MODE,
                ),
            )
        finally:
            connection.close()
        EVENTS_PUBLISHED.labels(routing_key).inc()
        logger.info(f'event {routing_key} published', extra={'routing_key': routing_key})
