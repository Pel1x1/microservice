from fastapi import Depends
from sqlalchemy.orm import Session

from app.database import get_db
from app.settings import settings
from app.clients.publisher import RabbitPublisher
from app.repositories.db_stock_repo import DbStockRepo
from app.services.stock_service import StockService


def build_stock_service(db: Session) -> StockService:
    return StockService(DbStockRepo(db), RabbitPublisher(settings.amqp_url, settings.exchange))


def get_stock_service(db: Session = Depends(get_db)) -> StockService:
    return build_stock_service(db)
