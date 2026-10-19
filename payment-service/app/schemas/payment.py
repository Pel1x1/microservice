from sqlalchemy import Column, Numeric, DateTime, Enum, Uuid

from app.schemas.base_schema import Base
from app.models.payment import PaymentStatuses


class Payment(Base):
    __tablename__ = 'payments'

    id = Column(Uuid, primary_key=True)
    order_id = Column(Uuid, nullable=False, unique=True)
    amount = Column(Numeric(12, 2), nullable=False)
    status = Column(Enum(PaymentStatuses), nullable=False, index=True)
    created_at = Column(DateTime(timezone=True), nullable=False)
