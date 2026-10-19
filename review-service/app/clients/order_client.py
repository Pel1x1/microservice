from abc import ABC, abstractmethod
from uuid import UUID

import requests
from pydantic import BaseModel


class OrderInfo(BaseModel):
    """То, что review-service знает о заказе из order-service."""
    id: UUID
    customer_id: UUID
    status: str
    part_ids: list[UUID]


class OrderClient(ABC):
    @abstractmethod
    def get_order(self, order_id: UUID) -> OrderInfo:
        """KeyError — заказа нет; ConnectionError — order-service недоступен."""


class HttpOrderClient(OrderClient):
    """Синхронный REST-вызов order-service (Sync REST из ПР4)."""

    def __init__(self, base_url: str, timeout: float = 3.0) -> None:
        self.base_url = base_url.rstrip('/')
        self.timeout = timeout

    def get_order(self, order_id: UUID) -> OrderInfo:
        try:
            response = requests.get(f'{self.base_url}/api/orders/{order_id}', timeout=self.timeout)
        except requests.RequestException as e:
            raise ConnectionError(f'order-service is unavailable: {e}') from e
        if response.status_code == 404:
            raise KeyError(order_id)
        if not response.ok:
            raise ConnectionError(f'order-service responded {response.status_code}')
        data = response.json()
        return OrderInfo(id=data['id'], customer_id=data['customer_id'], status=data['status'],
                         part_ids=[item['part_id'] for item in data['items']])
