from sqlalchemy import Column, String, DateTime, Enum, JSON, Uuid

from app.schemas.base_schema import Base
from app.models.order import OrderStatuses


class Order(Base):
    __tablename__ = 'orders'

    id = Column(Uuid, primary_key=True)
    customer_id = Column(Uuid, nullable=False, index=True)
    address = Column(String, nullable=False)
    items = Column(JSON, nullable=False)          # [{part_id, quantity, price}]
    status = Column(Enum(OrderStatuses), nullable=False, index=True)
    created_at = Column(DateTime(timezone=True), nullable=False)
