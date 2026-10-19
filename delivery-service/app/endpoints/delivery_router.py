from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query

from app.dependencies import get_delivery_service
from app.models.delivery import Delivery
from app.services.delivery_service import DeliveryService

delivery_router = APIRouter(prefix='/deliveries', tags=['Deliveries'])


@delivery_router.get('')
def get_deliveries(order_id: UUID | None = None,
                   offset: int = Query(0, ge=0),
                   count: int = Query(20, ge=1, le=100),
                   service: DeliveryService = Depends(get_delivery_service)) -> list[Delivery]:
    return service.get_deliveries(order_id, offset, count)


@delivery_router.get('/{delivery_id}')
def get_delivery(delivery_id: UUID,
                 service: DeliveryService = Depends(get_delivery_service)) -> Delivery:
    try:
        return service.get_delivery(delivery_id)
    except KeyError:
        raise HTTPException(404, f'Delivery with id={delivery_id} not found')


@delivery_router.post('/{delivery_id}:ship')
def ship_delivery(delivery_id: UUID,
                  service: DeliveryService = Depends(get_delivery_service)) -> Delivery:
    try:
        return service.ship_delivery(delivery_id)
    except KeyError:
        raise HTTPException(404, f'Delivery with id={delivery_id} not found')
    except ValueError as e:
        raise HTTPException(409, str(e))


@delivery_router.post('/{delivery_id}:deliver')
def deliver_delivery(delivery_id: UUID,
                     service: DeliveryService = Depends(get_delivery_service)) -> Delivery:
    try:
        return service.deliver_delivery(delivery_id)
    except KeyError:
        raise HTTPException(404, f'Delivery with id={delivery_id} not found')
    except ValueError as e:
        raise HTTPException(409, str(e))
