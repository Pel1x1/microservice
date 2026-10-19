from fastapi import Depends
from sqlalchemy.orm import Session

from app.database import get_db
from app.settings import settings
from app.clients.publisher import RabbitPublisher
from app.repositories.db_payment_repo import DbPaymentRepo
from app.services.payment_service import PaymentService


def build_payment_service(db: Session) -> PaymentService:
    return PaymentService(DbPaymentRepo(db), RabbitPublisher(settings.amqp_url, settings.exchange))


def get_payment_service(db: Session = Depends(get_db)) -> PaymentService:
    return build_payment_service(db)
