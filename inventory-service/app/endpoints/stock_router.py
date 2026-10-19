from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException

from app.dependencies import get_stock_service
from app.models.stock import Stock, Reservation, SetStockRequest
from app.services.stock_service import StockService

stock_router = APIRouter(prefix='/stocks', tags=['Stocks'])
reservation_router = APIRouter(prefix='/reservations', tags=['Reservations'])


@stock_router.get('')
def get_stocks(store_id: UUID | None = None,
               service: StockService = Depends(get_stock_service)) -> list[Stock]:
    return service.get_stocks(store_id)


@stock_router.get('/{part_id}')
def get_stock(part_id: UUID, service: StockService = Depends(get_stock_service)) -> Stock:
    try:
        return service.get_stock(part_id)
    except KeyError:
        raise HTTPException(404, f'Stock for part {part_id} not found')


@stock_router.put('/{part_id}')
def set_stock(part_id: UUID, body: SetStockRequest,
              service: StockService = Depends(get_stock_service)) -> Stock:
    try:
        return service.set_stock(part_id, body.store_id, body.price, body.quantity)
    except ValueError as e:
        raise HTTPException(409, str(e))


@reservation_router.get('')
def get_reservations(order_id: UUID | None = None,
                     service: StockService = Depends(get_stock_service)) -> list[Reservation]:
    return service.get_reservations(order_id)
