from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query

from app.dependencies import get_catalog_service
from app.models.part import Part, PublishPartRequest
from app.services.catalog_service import CatalogService

catalog_router = APIRouter(prefix='/parts', tags=['Catalog'])


@catalog_router.post('', status_code=201)
def publish_part(body: PublishPartRequest,
                 service: CatalogService = Depends(get_catalog_service)) -> Part:
    try:
        return service.publish_part(body.store_id, body.name, body.category, body.brand,
                                    body.compatible_cars)
    except ValueError as e:
        raise HTTPException(409, str(e))
    except ConnectionError as e:
        raise HTTPException(503, str(e))


@catalog_router.get('')
def search_parts(q: str | None = None,
                 category: str | None = None,
                 car: str | None = None,
                 store_id: UUID | None = None,
                 offset: int = Query(0, ge=0),
                 count: int = Query(20, ge=1, le=100),
                 service: CatalogService = Depends(get_catalog_service)) -> list[Part]:
    return service.search_parts(q, category, car, store_id, offset, count)


@catalog_router.get('/{part_id}')
def get_part(part_id: UUID, service: CatalogService = Depends(get_catalog_service)) -> Part:
    try:
        return service.get_part(part_id)
    except KeyError:
        raise HTTPException(404, f'Part with id={part_id} not found')


@catalog_router.post('/{part_id}:unpublish')
def unpublish_part(part_id: UUID, service: CatalogService = Depends(get_catalog_service)) -> Part:
    try:
        return service.unpublish_part(part_id)
    except KeyError:
        raise HTTPException(404, f'Part with id={part_id} not found')
    except ValueError as e:
        raise HTTPException(409, str(e))
