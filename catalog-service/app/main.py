from contextlib import asynccontextmanager

from fastapi import FastAPI

from app import rabbitmq
from app.database import engine
from app.schemas.base_schema import Base
from app.endpoints.catalog_router import catalog_router


@asynccontextmanager
async def lifespan(app: FastAPI):
    Base.metadata.create_all(bind=engine)
    connection = None
    try:
        connection = await rabbitmq.consume()
    except Exception as e:  # HTTP API работает и без брокера
        print(f'catalog-service: RabbitMQ is unavailable: {e}')
    yield
    if connection is not None:
        await connection.close()


app = FastAPI(title='Catalog Service', lifespan=lifespan)
app.include_router(catalog_router, prefix='/api')
