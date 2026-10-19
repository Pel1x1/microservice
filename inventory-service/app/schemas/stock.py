from sqlalchemy import Column, Integer, Numeric, Enum, Uuid

from app.schemas.base_schema import Base
from app.models.stock import ReservationStatuses


class Stock(Base):
    __tablename__ = 'stocks'

    part_id = Column(Uuid, primary_key=True)
    store_id = Column(Uuid, nullable=False, index=True)
    price = Column(Numeric(12, 2), nullable=False)
    quantity = Column(Integer, nullable=False)
    reserved = Column(Integer, nullable=False, default=0)


class Reservation(Base):
    __tablename__ = 'reservations'

    id = Column(Uuid, primary_key=True)
    order_id = Column(Uuid, nullable=False, index=True)
    part_id = Column(Uuid, nullable=False)
    quantity = Column(Integer, nullable=False)
    status = Column(Enum(ReservationStatuses), nullable=False)
