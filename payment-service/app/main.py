from contextlib import asynccontextmanager

from fastapi import FastAPI

from app import rabbitmq
from app.database import engine
from app.schemas.base_schema import Base
from app.endpoints.payment_router import payment_router


@asynccontextmanager
async def lifespan(app: FastAPI):
    Base.metadata.create_all(bind=engine)
    connection = None
    try:
        connection = await rabbitmq.consume()
    except Exception as e:  # HTTP API работает и без брокера
        print(f'payment-service: RabbitMQ is unavailable: {e}')
    yield
    if connection is not None:
        await connection.close()


app = FastAPI(title='Payment Service', lifespan=lifespan)
app.include_router(payment_router, prefix='/api')
