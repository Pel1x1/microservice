from uuid import UUID

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.part import Part, PartStatuses
from app.repositories.base_catalog_repo import BaseCatalogRepo
from app.schemas.part import Part as DBPart


class DbCatalogRepo(BaseCatalogRepo):
    def __init__(self, db: Session) -> None:
        self.db = db

    def get_parts(self, query: str | None = None, category: str | None = None,
                  car: str | None = None, store_id: UUID | None = None,
                  status: PartStatuses | None = None, offset: int = 0,
                  count: int | None = None) -> list[Part]:
        stmt = select(DBPart).order_by(DBPart.created_at)
        if query is not None:
            stmt = stmt.where(DBPart.name.ilike(f'%{query}%'))
        if category is not None:
            stmt = stmt.where(DBPart.category == category)
        if store_id is not None:
            stmt = stmt.where(DBPart.store_id == store_id)
        if status is not None:
            stmt = stmt.where(DBPart.status == status)
        parts = [Part.model_validate(p) for p in self.db.scalars(stmt).all()]
        if car is not None:  # совместимость хранится в JSON-колонке, фильтруем в приложении
            parts = [p for p in parts if car.lower() in [c.lower() for c in p.compatible_cars]]
        end = None if count is None else offset + count
        return parts[offset:end]

    def get_part(self, part_id: UUID) -> Part:
        part = self.db.get(DBPart, part_id)
        if part is None:
            raise KeyError(part_id)
        return Part.model_validate(part)

    def create_part(self, part: Part) -> Part:
        if self.db.get(DBPart, part.id) is not None:
            raise KeyError(part.id)
        self.db.add(DBPart(**part.model_dump()))
        self.db.commit()
        return part

    def save_part(self, part: Part) -> Part:
        db_part = self.db.get(DBPart, part.id)
        if db_part is None:
            raise KeyError(part.id)
        db_part.name = part.name
        db_part.category = part.category
        db_part.brand = part.brand
        db_part.compatible_cars = part.compatible_cars
        db_part.status = part.status
        self.db.commit()
        return part
