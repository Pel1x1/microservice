from uuid import UUID, uuid4
from datetime import datetime, timezone

from app.models.review import Review, Rating
from app.repositories.base_review_repo import BaseReviewRepo
from app.clients.order_client import OrderClient


class ReviewService:
    """Бизнес-логика контекста «Управление отзывами».

    KeyError        — отзыв не найден;
    ValueError      — нарушено бизнес-правило (товар не покупался, заказ не доставлен, повтор);
    ConnectionError — недоступен order-service.
    """

    def __init__(self, review_repo: BaseReviewRepo, order_client: OrderClient) -> None:
        self.review_repo = review_repo
        self.order_client = order_client

    def get_reviews(self, part_id: UUID | None = None, offset: int = 0,
                    count: int | None = None) -> list[Review]:
        return self.review_repo.get_reviews(part_id, offset, count)

    def get_review(self, review_id: UUID) -> Review:
        return self.review_repo.get_review(review_id)

    def create_review(self, order_id: UUID, part_id: UUID, author_id: UUID, rating: int,
                      text: str = '') -> Review:
        """Команда «Оставить отзыв на товар» (покупатель, после «Посылка доставлена»)."""
        self._check_purchase(order_id, part_id, author_id)  # вложенный синхронный вызов order-service
        if self.review_repo.find_review(order_id, part_id) is not None:
            raise ValueError('Отзыв на эту запчасть из этого заказа уже оставлен')
        review = Review(id=uuid4(), order_id=order_id, part_id=part_id, author_id=author_id,
                        rating=rating, text=text, created_at=datetime.now(timezone.utc))
        return self.review_repo.create_review(review)

    def get_rating(self, part_id: UUID) -> Rating:
        """Рейтинг запчасти: среднее по всем её отзывам."""
        reviews = self.review_repo.get_reviews(part_id=part_id)
        if not reviews:
            return Rating(part_id=part_id, count=0, average=None)
        average = sum(r.rating for r in reviews) / len(reviews)
        return Rating(part_id=part_id, count=len(reviews), average=round(average, 2))

    # --- вложенные вспомогательные функции ---

    def _check_purchase(self, order_id: UUID, part_id: UUID, author_id: UUID) -> None:
        try:
            order = self.order_client.get_order(order_id)
        except KeyError:
            raise ValueError(f'Заказ {order_id} не найден')
        if order.customer_id != author_id:
            raise ValueError('Заказ оформлен другим покупателем')
        if order.status != 'completed':
            raise ValueError(f'Отзыв можно оставить только на доставленный заказ (статус: {order.status})')
        if part_id not in order.part_ids:
            raise ValueError(f'Запчасти {part_id} нет в заказе {order_id}')
