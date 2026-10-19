from contextlib import asynccontextmanager

from fastapi import FastAPI

from app import rabbitmq
from app.database import engine
from app.schemas.base_schema import Base
from app.endpoints.stock_router import stock_router, reservation_router


@asynccontextmanager
async def lifespan(app: FastAPI):
    Base.metadata.create_all(bind=engine)
    connection = None
    try:
        connection = await rabbitmq.consume()
    except Exception as e:  # HTTP API работает и без брокера
        print(f'inventory-service: RabbitMQ is unavailable: {e}')
    yield
    if connection is not None:
        await connection.close()


app = FastAPI(title='Inventory Service', lifespan=lifespan)
app.include_router(stock_router, prefix='/api')
app.include_router(reservation_router, prefix='/api')
