import asyncio
import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI

from app import rabbitmq
from app.database import engine
from app.observability import setup_observability
from app.schemas.base_schema import Base
from app.endpoints.catalog_router import catalog_router

logger = logging.getLogger('automarket')


async def consume_with_retry(app: FastAPI) -> None:
    """Подключение к RabbitMQ в фоне: если брокер ещё не готов, повторяем попытки
    (1, 2, 4 … 30 с). HTTP API работает и без брокера. После первого подключения
    обрывы связи обрабатывает connect_robust."""
    delay = 1
    while True:
        try:
            app.state.amqp = await rabbitmq.consume()
            return
        except Exception as e:
            logger.warning(f'RabbitMQ is unavailable, retry in {delay}s: {e}')
            await asyncio.sleep(delay)
            delay = min(delay * 2, 30)


@asynccontextmanager
async def lifespan(app: FastAPI):
    Base.metadata.create_all(bind=engine)
    app.state.amqp = None
    consumer = asyncio.create_task(consume_with_retry(app))
    yield
    consumer.cancel()
    if app.state.amqp is not None:
        await app.state.amqp.close()


app = FastAPI(title='Catalog Service', lifespan=lifespan)
setup_observability(app, 'catalog-service', engine)  # ПР10: метрики, JSON-логи, трассировка
app.include_router(catalog_router, prefix='/api')
