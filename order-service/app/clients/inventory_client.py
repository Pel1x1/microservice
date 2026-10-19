from abc import ABC, abstractmethod
from uuid import UUID
from decimal import Decimal

import requests
from pydantic import BaseModel


class StockInfo(BaseModel):
    """То, что order-service знает об остатке из inventory-service."""
    part_id: UUID
    price: Decimal
    available: int


class InventoryClient(ABC):
    @abstractmethod
    def get_stock(self, part_id: UUID) -> StockInfo:
        """KeyError — запчасти нет; ConnectionError — inventory-service недоступен."""


class HttpInventoryClient(InventoryClient):
    """Синхронный REST-вызов inventory-service (Sync REST из ПР4)."""

    def __init__(self, base_url: str, timeout: float = 3.0) -> None:
        self.base_url = base_url.rstrip('/')
        self.timeout = timeout

    def get_stock(self, part_id: UUID) -> StockInfo:
        try:
            response = requests.get(f'{self.base_url}/api/stocks/{part_id}', timeout=self.timeout)
        except requests.RequestException as e:
            raise ConnectionError(f'inventory-service is unavailable: {e}') from e
        if response.status_code == 404:
            raise KeyError(part_id)
        if not response.ok:
            raise ConnectionError(f'inventory-service responded {response.status_code}')
        return StockInfo.model_validate(response.json())
