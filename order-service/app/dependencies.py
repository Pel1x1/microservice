from fastapi import Depends
from sqlalchemy.orm import Session

from app.database import get_db
from app.settings import settings
from app.clients.publisher import RabbitPublisher
from app.clients.inventory_client import HttpInventoryClient
from app.repositories.db_order_repo import DbOrderRepo
from app.services.order_service import OrderService


def build_order_service(db: Session) -> OrderService:
    return OrderService(DbOrderRepo(db), HttpInventoryClient(settings.inventory_url),
                        RabbitPublisher(settings.amqp_url, settings.exchange))


def get_order_service(db: Session = Depends(get_db)) -> OrderService:
    return build_order_service(db)
