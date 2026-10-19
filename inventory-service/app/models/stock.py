import enum
from uuid import UUID
from decimal import Decimal

from pydantic import BaseModel, ConfigDict, Field, computed_field


class Stock(BaseModel):
    """Остаток запчасти на складе продавца (строка прайс-листа)."""
    model_config = ConfigDict(from_attributes=True, validate_assignment=True)

    part_id: UUID
    store_id: UUID
    price: Decimal = Field(gt=0, decimal_places=2)
    quantity: int = Field(ge=0)
    reserved: int = Field(default=0, ge=0)

    @computed_field
    @property
    def available(self) -> int:
        return self.quantity - self.reserved


class ReservationStatuses(enum.Enum):
    ACTIVE = 'active'
    RELEASED = 'released'


class Reservation(BaseModel):
    """Резерв: закрепление количества товара за оформленным заказом."""
    model_config = ConfigDict(from_attributes=True, validate_assignment=True)

    id: UUID
    order_id: UUID
    part_id: UUID
    quantity: int = Field(gt=0)
    status: ReservationStatuses = ReservationStatuses.ACTIVE


class SetStockRequest(BaseModel):
    store_id: UUID
    price: Decimal = Field(gt=0, decimal_places=2)
    quantity: int = Field(ge=0)


class ReserveItem(BaseModel):
    part_id: UUID
    quantity: int = Field(gt=0)
