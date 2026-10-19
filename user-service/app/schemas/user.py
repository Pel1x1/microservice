from sqlalchemy import Column, String, Boolean, DateTime, Enum, Uuid

from app.schemas.base_schema import Base
from app.models.user import UserRoles


class User(Base):
    __tablename__ = 'users'

    id = Column(Uuid, primary_key=True)
    email = Column(String, nullable=False, unique=True)
    name = Column(String, nullable=False)
    role = Column(Enum(UserRoles), nullable=False, index=True)
    is_blocked = Column(Boolean, nullable=False, default=False)
    created_at = Column(DateTime(timezone=True), nullable=False)
