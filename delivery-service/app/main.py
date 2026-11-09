import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI

from app import rabbitmq
from app.database import engine
from app.observability import setup_observability
from app.schemas.base_schema import Base
from app.endpoints.delivery_router import delivery_router


@asynccontextmanager
async def lifespan(app: FastAPI):
    Base.metadata.create_all(bind=engine)
    connection = None
    try:
        connection = await rabbitmq.consume()
    except Exception as e:  # HTTP API работает и без брокера
        logging.getLogger('automarket').warning(f'RabbitMQ is unavailable: {e}')
    yield
    if connection is not None:
        await connection.close()


app = FastAPI(title='Delivery Service', lifespan=lifespan)
setup_observability(app, 'delivery-service', engine)  # ПР10: метрики, JSON-логи, трассировка
app.include_router(delivery_router, prefix='/api')
