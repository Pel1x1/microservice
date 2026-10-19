from fastapi import Depends
from sqlalchemy.orm import Session

from app.database import get_db
from app.settings import settings
from app.clients.publisher import RabbitPublisher
from app.repositories.db_delivery_repo import DbDeliveryRepo
from app.services.delivery_service import DeliveryService


def build_delivery_service(db: Session) -> DeliveryService:
    return DeliveryService(DbDeliveryRepo(db), RabbitPublisher(settings.amqp_url, settings.exchange))


def get_delivery_service(db: Session = Depends(get_db)) -> DeliveryService:
    return build_delivery_service(db)
