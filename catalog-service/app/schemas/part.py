from sqlalchemy import Column, String, DateTime, Enum, JSON, Uuid

from app.schemas.base_schema import Base
from app.models.part import PartStatuses


class Part(Base):
    __tablename__ = 'parts'

    id = Column(Uuid, primary_key=True)
    store_id = Column(Uuid, nullable=False, index=True)
    name = Column(String, nullable=False)
    category = Column(String, nullable=False, index=True)
    brand = Column(String, nullable=False)
    compatible_cars = Column(JSON, nullable=False)    # ["Toyota Camry 2018", ...]
    status = Column(Enum(PartStatuses), nullable=False, index=True)
    created_at = Column(DateTime(timezone=True), nullable=False)
