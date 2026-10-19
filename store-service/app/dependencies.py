from fastapi import Depends
from sqlalchemy.orm import Session

from app.database import get_db
from app.settings import settings
from app.clients.publisher import RabbitPublisher
from app.repositories.db_store_repo import DbStoreRepo
from app.services.store_service import StoreService


def build_store_service(db: Session) -> StoreService:
    return StoreService(DbStoreRepo(db), RabbitPublisher(settings.amqp_url, settings.exchange))


def get_store_service(db: Session = Depends(get_db)) -> StoreService:
    return build_store_service(db)
