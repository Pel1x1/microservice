from abc import ABC, abstractmethod
from uuid import UUID

import requests
from pydantic import BaseModel


class StoreInfo(BaseModel):
    """То, что catalog-service знает о магазине из store-service."""
    id: UUID
    status: str


class StoreClient(ABC):
    @abstractmethod
    def get_store(self, store_id: UUID) -> StoreInfo:
        """KeyError — магазина нет; ConnectionError — store-service недоступен."""


class HttpStoreClient(StoreClient):
    """Синхронный REST-вызов store-service (Sync REST из ПР4)."""

    def __init__(self, base_url: str, timeout: float = 3.0) -> None:
        self.base_url = base_url.rstrip('/')
        self.timeout = timeout

    def get_store(self, store_id: UUID) -> StoreInfo:
        try:
            response = requests.get(f'{self.base_url}/api/stores/{store_id}', timeout=self.timeout)
        except requests.RequestException as e:
            raise ConnectionError(f'store-service is unavailable: {e}') from e
        if response.status_code == 404:
            raise KeyError(store_id)
        if not response.ok:
            raise ConnectionError(f'store-service responded {response.status_code}')
        return StoreInfo.model_validate(response.json())
