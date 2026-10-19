from contextlib import asynccontextmanager

from fastapi import FastAPI

from app.database import engine
from app.schemas.base_schema import Base
from app.endpoints.review_router import review_router, rating_router


@asynccontextmanager
async def lifespan(app: FastAPI):
    Base.metadata.create_all(bind=engine)
    yield


app = FastAPI(title='Review Service', lifespan=lifespan)
app.include_router(review_router, prefix='/api')
app.include_router(rating_router, prefix='/api')
