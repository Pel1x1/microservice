from fastapi import Depends
from sqlalchemy.orm import Session

from app.database import get_db
from app.settings import settings
from app.clients.order_client import HttpOrderClient
from app.repositories.db_review_repo import DbReviewRepo
from app.services.review_service import ReviewService


def build_review_service(db: Session) -> ReviewService:
    return ReviewService(DbReviewRepo(db), HttpOrderClient(settings.order_url))


def get_review_service(db: Session = Depends(get_db)) -> ReviewService:
    return build_review_service(db)
