from contextlib import asynccontextmanager

from fastapi import FastAPI

from app.database import engine
from app.schemas.base_schema import Base
from app.endpoints.user_router import user_router


@asynccontextmanager
async def lifespan(app: FastAPI):
    Base.metadata.create_all(bind=engine)
    yield


app = FastAPI(title='User Service', lifespan=lifespan)
app.include_router(user_router, prefix='/api')
