from uuid import UUID

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.order import Order, OrderStatuses
from app.repositories.base_order_repo import BaseOrderRepo
from app.schemas.order import Order as DBOrder


class DbOrderRepo(BaseOrderRepo):
    def __init__(self, db: Session) -> None:
        self.db = db

    def get_orders(self, customer_id: UUID | None = None, status: OrderStatuses | None = None,
                   offset: int = 0, count: int | None = None) -> list[Order]:
        query = select(DBOrder).order_by(DBOrder.created_at)
        if customer_id is not None:
            query = query.where(DBOrder.customer_id == customer_id)
        if status is not None:
            query = query.where(DBOrder.status == status)
        query = query.offset(offset)
        if count is not None:
            query = query.limit(count)
        return [Order.model_validate(o) for o in self.db.scalars(query).all()]

    def get_order(self, order_id: UUID) -> Order:
        order = self.db.get(DBOrder, order_id)
        if order is None:
            raise KeyError(order_id)
        return Order.model_validate(order)

    def create_order(self, order: Order) -> Order:
        if self.db.get(DBOrder, order.id) is not None:
            raise KeyError(order.id)
        self.db.add(DBOrder(
            id=order.id,
            customer_id=order.customer_id,
            address=order.address,
            items=[item.model_dump(mode='json') for item in order.items],
            status=order.status,
            created_at=order.created_at,
        ))
        self.db.commit()
        return order

    def set_status(self, order: Order) -> Order:
        db_order = self.db.get(DBOrder, order.id)
        if db_order is None:
            raise KeyError(order.id)
        db_order.status = order.status
        self.db.commit()
        return order
