from uuid import UUID

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.stock import Stock, Reservation
from app.repositories.base_stock_repo import BaseStockRepo
from app.schemas.stock import Stock as DBStock, Reservation as DBReservation


class DbStockRepo(BaseStockRepo):
    """Хранилище в PostgreSQL. Проверяется интеграционными тестами."""

    def __init__(self, db: Session) -> None:
        self.db = db

    def get_stocks(self, store_id: UUID | None = None) -> list[Stock]:
        query = select(DBStock).order_by(DBStock.part_id)
        if store_id is not None:
            query = query.where(DBStock.store_id == store_id)
        return [Stock.model_validate(s) for s in self.db.scalars(query).all()]

    def get_stock(self, part_id: UUID) -> Stock:
        stock = self.db.get(DBStock, part_id)
        if stock is None:
            raise KeyError(part_id)
        return Stock.model_validate(stock)

    def save_stock(self, stock: Stock) -> Stock:
        db_stock = self.db.get(DBStock, stock.part_id)
        if db_stock is None:
            db_stock = DBStock(part_id=stock.part_id)
            self.db.add(db_stock)
        db_stock.store_id = stock.store_id
        db_stock.price = stock.price
        db_stock.quantity = stock.quantity
        db_stock.reserved = stock.reserved
        self.db.commit()
        return stock

    def create_reservation(self, reservation: Reservation) -> Reservation:
        if self.db.get(DBReservation, reservation.id) is not None:
            raise KeyError(reservation.id)
        self.db.add(DBReservation(id=reservation.id, order_id=reservation.order_id,
                                  part_id=reservation.part_id, quantity=reservation.quantity,
                                  status=reservation.status))
        self.db.commit()
        return reservation

    def get_reservations(self, order_id: UUID | None = None) -> list[Reservation]:
        query = select(DBReservation).order_by(DBReservation.id)
        if order_id is not None:
            query = query.where(DBReservation.order_id == order_id)
        return [Reservation.model_validate(r) for r in self.db.scalars(query).all()]

    def save_reservation(self, reservation: Reservation) -> Reservation:
        db_reservation = self.db.get(DBReservation, reservation.id)
        if db_reservation is None:
            raise KeyError(reservation.id)
        db_reservation.status = reservation.status
        self.db.commit()
        return reservation
