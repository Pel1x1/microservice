import asyncio
import json
import logging
from typing import Callable

from aio_pika import connect_robust, ExchangeType
from aio_pika.abc import AbstractIncomingMessage, AbstractRobustConnection

from app.settings import settings
from app.observability import EVENTS_CONSUMED
from app.database import SessionLocal
from app.dependencies import build_catalog_service
from app.services.catalog_service import CatalogService

logger = logging.getLogger('automarket')


def _run_with_service(handler: Callable[[CatalogService, dict], None], payload: dict) -> None:
    db = SessionLocal()
    try:
        handler(build_catalog_service(db), payload)
    finally:
        db.close()


def _make_consumer(handler: Callable[[CatalogService, dict], None]):
    async def on_message(msg: AbstractIncomingMessage) -> None:
        async with msg.process(requeue=False):
            try:
                payload = json.loads(msg.body.decode())
                # синхронная работа с БД выполняется в отдельном потоке
                await asyncio.to_thread(_run_with_service, handler, payload)
                EVENTS_CONSUMED.labels(msg.routing_key, 'ok').inc()
                logger.info(f'event {msg.routing_key} processed', extra={'routing_key': msg.routing_key})
            except Exception:
                EVENTS_CONSUMED.labels(msg.routing_key, 'error').inc()
                logger.exception(f'event {msg.routing_key} failed', extra={'routing_key': msg.routing_key})
                raise
    return on_message


# routing key -> обработчик
SUBSCRIPTIONS = {
    'store.blocked': CatalogService.handle_store_blocked,
}


async def consume() -> AbstractRobustConnection:
    connection = await connect_robust(settings.amqp_url)
    channel = await connection.channel()
    await channel.set_qos(prefetch_count=10)
    exchange = await channel.declare_exchange(settings.exchange, ExchangeType.TOPIC, durable=True)

    for routing_key, handler in SUBSCRIPTIONS.items():
        queue_name = f'{settings.queue_prefix}_catalog_{routing_key.replace(".", "_")}'
        queue = await channel.declare_queue(queue_name, durable=True)
        await queue.bind(exchange, routing_key=routing_key)
        await queue.consume(_make_consumer(handler))

    logger.info(f'started RabbitMQ consuming: {", ".join(SUBSCRIPTIONS)}')
    return connection
