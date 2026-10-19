from sqlalchemy import Column, String, DateTime, Enum, Uuid

from app.schemas.base_schema import Base
from app.models.store import StoreStatuses


class Store(Base):
    __tablename__ = 'stores'

    id = Column(Uuid, primary_key=True)
    owner_id = Column(Uuid, nullable=False, index=True)
    name = Column(String, nullable=False)
    status = Column(Enum(StoreStatuses), nullable=False, index=True)
    created_at = Column(DateTime(timezone=True), nullable=False)
