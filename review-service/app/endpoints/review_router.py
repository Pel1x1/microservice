from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query

from app.dependencies import get_review_service
from app.models.review import Review, Rating, CreateReviewRequest
from app.services.review_service import ReviewService

review_router = APIRouter(prefix='/reviews', tags=['Reviews'])
rating_router = APIRouter(prefix='/ratings', tags=['Ratings'])


@review_router.post('', status_code=201)
def create_review(body: CreateReviewRequest,
                  service: ReviewService = Depends(get_review_service)) -> Review:
    try:
        return service.create_review(body.order_id, body.part_id, body.author_id, body.rating,
                                     body.text)
    except ValueError as e:
        raise HTTPException(409, str(e))
    except ConnectionError as e:
        raise HTTPException(503, str(e))


@review_router.get('')
def get_reviews(part_id: UUID | None = None,
                offset: int = Query(0, ge=0),
                count: int = Query(20, ge=1, le=100),
                service: ReviewService = Depends(get_review_service)) -> list[Review]:
    return service.get_reviews(part_id, offset, count)


@review_router.get('/{review_id}')
def get_review(review_id: UUID, service: ReviewService = Depends(get_review_service)) -> Review:
    try:
        return service.get_review(review_id)
    except KeyError:
        raise HTTPException(404, f'Review with id={review_id} not found')


@rating_router.get('/{part_id}')
def get_rating(part_id: UUID, service: ReviewService = Depends(get_review_service)) -> Rating:
    return service.get_rating(part_id)
