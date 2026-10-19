from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query

from app.dependencies import get_store_service
from app.models.store import Store, StoreStatuses, CreateStoreRequest
from app.services.store_service import StoreService

store_router = APIRouter(prefix='/stores', tags=['Stores'])


@store_router.post('', status_code=201)
def create_store(body: CreateStoreRequest,
                 service: StoreService = Depends(get_store_service)) -> Store:
    try:
        return service.create_store(body.owner_id, body.name)
    except ValueError as e:
        raise HTTPException(409, str(e))


@store_router.get('')
def get_stores(status: StoreStatuses | None = None,
               owner_id: UUID | None = None,
               offset: int = Query(0, ge=0),
               count: int = Query(20, ge=1, le=100),
               service: StoreService = Depends(get_store_service)) -> list[Store]:
    return service.get_stores(status, owner_id, offset, count)


@store_router.get('/{store_id}')
def get_store(store_id: UUID, service: StoreService = Depends(get_store_service)) -> Store:
    try:
        return service.get_store(store_id)
    except KeyError:
        raise HTTPException(404, f'Store with id={store_id} not found')


@store_router.post('/{store_id}:verify')
def verify_store(store_id: UUID, service: StoreService = Depends(get_store_service)) -> Store:
    try:
        return service.verify_store(store_id)
    except KeyError:
        raise HTTPException(404, f'Store with id={store_id} not found')
    except ValueError as e:
        raise HTTPException(409, str(e))


@store_router.post('/{store_id}:block')
def block_store(store_id: UUID, service: StoreService = Depends(get_store_service)) -> Store:
    try:
        return service.block_store(store_id)
    except KeyError:
        raise HTTPException(404, f'Store with id={store_id} not found')
    except ValueError as e:
        raise HTTPException(409, str(e))
