from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query

from app.dependencies import get_payment_service
from app.models.payment import Payment
from app.services.payment_service import PaymentService

payment_router = APIRouter(prefix='/payments', tags=['Payments'])


@payment_router.get('')
def get_payments(order_id: UUID | None = None,
                 offset: int = Query(0, ge=0),
                 count: int = Query(20, ge=1, le=100),
                 service: PaymentService = Depends(get_payment_service)) -> list[Payment]:
    return service.get_payments(order_id, offset, count)


@payment_router.get('/{payment_id}')
def get_payment(payment_id: UUID, service: PaymentService = Depends(get_payment_service)) -> Payment:
    try:
        return service.get_payment(payment_id)
    except KeyError:
        raise HTTPException(404, f'Payment with id={payment_id} not found')


# Ответ внешнего эквайринга (webhook): <ресурс>/{id}:<действие>
@payment_router.post('/{payment_id}:confirm')
def confirm_payment(payment_id: UUID,
                    service: PaymentService = Depends(get_payment_service)) -> Payment:
    try:
        return service.confirm_payment(payment_id)
    except KeyError:
        raise HTTPException(404, f'Payment with id={payment_id} not found')
    except ValueError as e:
        raise HTTPException(409, str(e))


@payment_router.post('/{payment_id}:fail')
def fail_payment(payment_id: UUID,
                 service: PaymentService = Depends(get_payment_service)) -> Payment:
    try:
        return service.fail_payment(payment_id)
    except KeyError:
        raise HTTPException(404, f'Payment with id={payment_id} not found')
    except ValueError as e:
        raise HTTPException(409, str(e))
