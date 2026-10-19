from contextlib import asynccontextmanager

from fastapi import FastAPI

from app.database import engine
from app.schemas.base_schema import Base
from app.endpoints.store_router import store_router


@asynccontextmanager
async def lifespan(app: FastAPI):
    Base.metadata.create_all(bind=engine)
    yield


app = FastAPI(title='Store Service', lifespan=lifespan)
app.include_router(store_router, prefix='/api')
