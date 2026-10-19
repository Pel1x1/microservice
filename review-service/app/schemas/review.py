from sqlalchemy import Column, Integer, String, DateTime, Uuid, UniqueConstraint

from app.schemas.base_schema import Base


class Review(Base):
    __tablename__ = 'reviews'
    __table_args__ = (UniqueConstraint('order_id', 'part_id', name='uq_review_order_part'),)

    id = Column(Uuid, primary_key=True)
    order_id = Column(Uuid, nullable=False)
    part_id = Column(Uuid, nullable=False, index=True)
    author_id = Column(Uuid, nullable=False)
    rating = Column(Integer, nullable=False)
    text = Column(String, nullable=False, default='')
    created_at = Column(DateTime(timezone=True), nullable=False)
