import asyncio
import json
import traceback
from typing import Callable

from aio_pika import connect_robust, ExchangeType
from aio_pika.abc import AbstractIncomingMessage, AbstractRobustConnection

from app.settings import settings
from app.database import SessionLocal
from app.dependencies import build_order_service
from app.services.order_service import OrderService


def _run_with_service(handler: Callable[[OrderService, dict], None], payload: dict) -> None:
    db = SessionLocal()
    try:
        handler(build_order_service(db), payload)
    finally:
        db.close()


def _make_consumer(handler: Callable[[OrderService, dict], None]):
    async def on_message(msg: AbstractIncomingMessage) -> None:
        async with msg.process(requeue=False):
            try:
                payload = json.loads(msg.body.decode())
                # синхронная работа с БД выполняется в отдельном потоке
                await asyncio.to_thread(_run_with_service, handler, payload)
            except Exception:
                traceback.print_exc()
                raise
    return on_message


# routing key -> обработчик
SUBSCRIPTIONS = {
    'payment.confirmed': OrderService.handle_payment_confirmed,     # от payment-service
    'delivery.delivered': OrderService.handle_delivery_delivered,   # от delivery-service
    'inventory.reserve_failed': OrderService.handle_reserve_failed, # от inventory-service
}


async def consume() -> AbstractRobustConnection:
    connection = await connect_robust(settings.amqp_url)
    channel = await connection.channel()
    await channel.set_qos(prefetch_count=10)
    exchange = await channel.declare_exchange(settings.exchange, ExchangeType.TOPIC, durable=True)

    for routing_key, handler in SUBSCRIPTIONS.items():
        queue_name = f'{settings.queue_prefix}_order_{routing_key.replace(".", "_")}'
        queue = await channel.declare_queue(queue_name, durable=True)
        await queue.bind(exchange, routing_key=routing_key)
        await queue.consume(_make_consumer(handler))

    print('order-service: started RabbitMQ consuming...')
    return connection
