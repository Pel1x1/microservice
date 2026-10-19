from sqlalchemy import Column, String, DateTime, Enum, Uuid

from app.schemas.base_schema import Base
from app.models.delivery import DeliveryStatuses


class Delivery(Base):
    __tablename__ = 'deliveries'

    id = Column(Uuid, primary_key=True)
    order_id = Column(Uuid, nullable=False, unique=True)
    address = Column(String, nullable=False)
    status = Column(Enum(DeliveryStatuses), nullable=False, index=True)
    created_at = Column(DateTime(timezone=True), nullable=False)
