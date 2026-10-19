# /tests/integration/test_stock_repo_db.py
from uuid import uuid4
from decimal import Decimal

import pytest
from sqlalchemy.orm import Session

from app.models.stock import Stock, Reservation, ReservationStatuses, ReserveItem
from app.repositories.db_stock_repo import DbStockRepo
from app.services.stock_service import StockService


@pytest.fixture()
def repo(db: Session) -> DbStockRepo:
    return DbStockRepo(db)


@pytest.fixture()
def stock() -> Stock:
    return Stock(part_id=uuid4(), store_id=uuid4(), price=Decimal('2500.00'), quantity=10)


def test_empty_list(repo: DbStockRepo) -> None:
    assert repo.get_stocks() == []


def test_save_and_get_stock(repo: DbStockRepo, stock: Stock) -> None:
    repo.save_stock(stock)
    assert repo.get_stock(stock.part_id) == stock


def test_get_stock_not_found(repo: DbStockRepo) -> None:
    with pytest.raises(KeyError):
        repo.get_stock(uuid4())


def test_save_stock_updates_existing(repo: DbStockRepo, stock: Stock) -> None:
    repo.save_stock(stock)
    stock.quantity = 3
    stock.reserved = 1
    repo.save_stock(stock)
    saved = repo.get_stock(stock.part_id)
    assert (saved.quantity, saved.reserved, saved.available) == (3, 1, 2)
    assert len(repo.get_stocks()) == 1


def test_get_stocks_filter_by_store(repo: DbStockRepo, stock: Stock) -> None:
    other = Stock(part_id=uuid4(), store_id=uuid4(), price=Decimal('10.00'), quantity=1)
    repo.save_stock(stock)
    repo.save_stock(other)
    assert repo.get_stocks(stock.store_id) == [stock]
    assert len(repo.get_stocks()) == 2


def test_reservation_create_get_update(repo: DbStockRepo, stock: Stock) -> None:
    repo.save_stock(stock)
    reservation = Reservation(id=uuid4(), order_id=uuid4(), part_id=stock.part_id, quantity=2)
    assert repo.create_reservation(reservation) == reservation
    assert repo.get_reservations(reservation.order_id) == [reservation]

    reservation.status = ReservationStatuses.RELEASED
    repo.save_reservation(reservation)
    assert repo.get_reservations(reservation.order_id)[0].status == ReservationStatuses.RELEASED


def test_reservation_repeat(repo: DbStockRepo) -> None:
    reservation = Reservation(id=uuid4(), order_id=uuid4(), part_id=uuid4(), quantity=1)
    repo.create_reservation(reservation)
    with pytest.raises(KeyError):
        repo.create_reservation(reservation)


def test_save_unknown_reservation(repo: DbStockRepo) -> None:
    with pytest.raises(KeyError):
        repo.save_reservation(Reservation(id=uuid4(), order_id=uuid4(), part_id=uuid4(),
                                          quantity=1))


def test_service_reserve_and_release_with_db(repo: DbStockRepo, stock: Stock) -> None:
    """Бизнес-логика поверх настоящей БД: резерв и его снятие."""
    service = StockService(repo)
    repo.save_stock(stock)
    order_id = uuid4()
    service.reserve(order_id, [ReserveItem(part_id=stock.part_id, quantity=4)])
    assert repo.get_stock(stock.part_id).available == 6
    service.release(order_id)
    assert repo.get_stock(stock.part_id).available == 10
