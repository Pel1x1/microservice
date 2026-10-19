from uuid import UUID

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.delivery import Delivery
from app.repositories.base_delivery_repo import BaseDeliveryRepo
from app.schemas.delivery import Delivery as DBDelivery


class DbDeliveryRepo(BaseDeliveryRepo):
    def __init__(self, db: Session) -> None:
        self.db = db

    def get_deliveries(self, order_id: UUID | None = None, offset: int = 0,
                       count: int | None = None) -> list[Delivery]:
        query = select(DBDelivery).order_by(DBDelivery.created_at)
        if order_id is not None:
            query = query.where(DBDelivery.order_id == order_id)
        query = query.offset(offset)
        if count is not None:
            query = query.limit(count)
        return [Delivery.model_validate(d) for d in self.db.scalars(query).all()]

    def get_delivery(self, delivery_id: UUID) -> Delivery:
        delivery = self.db.get(DBDelivery, delivery_id)
        if delivery is None:
            raise KeyError(delivery_id)
        return Delivery.model_validate(delivery)

    def find_by_order(self, order_id: UUID) -> Delivery | None:
        delivery = self.db.scalars(select(DBDelivery).where(DBDelivery.order_id == order_id)).first()
        return None if delivery is None else Delivery.model_validate(delivery)

    def create_delivery(self, delivery: Delivery) -> Delivery:
        if self.db.get(DBDelivery, delivery.id) is not None:
            raise KeyError(delivery.id)
        self.db.add(DBDelivery(**delivery.model_dump()))
        self.db.commit()
        return delivery

    def save_delivery(self, delivery: Delivery) -> Delivery:
        db_delivery = self.db.get(DBDelivery, delivery.id)
        if db_delivery is None:
            raise KeyError(delivery.id)
        db_delivery.status = delivery.status
        self.db.commit()
        return delivery
