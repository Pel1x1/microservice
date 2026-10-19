from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query

from app.dependencies import get_order_service
from app.models.order import Order, OrderStatuses, CreateOrderRequest, CancelOrderRequest
from app.services.order_service import OrderService

order_router = APIRouter(prefix='/orders', tags=['Orders'])


@order_router.post('', status_code=201)
def create_order(body: CreateOrderRequest,
                 service: OrderService = Depends(get_order_service)) -> Order:
    try:
        return service.create_order(body.customer_id, body.address, body.items)
    except ValueError as e:
        raise HTTPException(400, str(e))
    except ConnectionError as e:
        raise HTTPException(503, str(e))


@order_router.get('')
def get_orders(customer_id: UUID | None = None,
               status: OrderStatuses | None = None,
               offset: int = Query(0, ge=0),
               count: int = Query(20, ge=1, le=100),
               service: OrderService = Depends(get_order_service)) -> list[Order]:
    return service.get_orders(customer_id, status, offset, count)


@order_router.get('/{order_id}')
def get_order(order_id: UUID, service: OrderService = Depends(get_order_service)) -> Order:
    try:
        return service.get_order(order_id)
    except KeyError:
        raise HTTPException(404, f'Order with id={order_id} not found')


# Пользовательские операции (ПР6): <ресурс>/{id}:<действие>
@order_router.post('/{order_id}:assemble')
def assemble_order(order_id: UUID, service: OrderService = Depends(get_order_service)) -> Order:
    try:
        return service.assemble_order(order_id)
    except KeyError:
        raise HTTPException(404, f'Order with id={order_id} not found')
    except ValueError as e:
        raise HTTPException(409, str(e))


@order_router.post('/{order_id}:cancel')
def cancel_order(order_id: UUID,
                 body: CancelOrderRequest | None = None,
                 service: OrderService = Depends(get_order_service)) -> Order:
    try:
        return service.cancel_order(order_id, body.reason if body else None)
    except KeyError:
        raise HTTPException(404, f'Order with id={order_id} not found')
    except ValueError as e:
        raise HTTPException(409, str(e))
