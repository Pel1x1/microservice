from fastapi import Depends
from sqlalchemy.orm import Session

from app.database import get_db
from app.settings import settings
from app.clients.publisher import RabbitPublisher
from app.repositories.db_user_repo import DbUserRepo
from app.services.user_service import UserService


def build_user_service(db: Session) -> UserService:
    return UserService(DbUserRepo(db), RabbitPublisher(settings.amqp_url, settings.exchange))


def get_user_service(db: Session = Depends(get_db)) -> UserService:
    return build_user_service(db)
