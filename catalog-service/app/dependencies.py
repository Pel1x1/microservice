from fastapi import Depends
from sqlalchemy.orm import Session

from app.database import get_db
from app.settings import settings
from app.clients.publisher import RabbitPublisher
from app.clients.store_client import HttpStoreClient
from app.repositories.db_catalog_repo import DbCatalogRepo
from app.services.catalog_service import CatalogService


def build_catalog_service(db: Session) -> CatalogService:
    return CatalogService(DbCatalogRepo(db), HttpStoreClient(settings.store_url), RabbitPublisher(settings.amqp_url, settings.exchange))


def get_catalog_service(db: Session = Depends(get_db)) -> CatalogService:
    return build_catalog_service(db)
