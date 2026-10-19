import enum
from uuid import UUID
from decimal import Decimal
from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field, computed_field


class OrderStatuses(enum.Enum):
    CREATED = 'created'        # заказ оформлен покупателем
    CONFIRMED = 'confirmed'    # оплата подтверждена
    ASSEMBLED = 'assembled'    # продавец собрал заказ
    COMPLETED = 'completed'    # посылка доставлена
    CANCELED = 'canceled'      # заказ отменён


class OrderItem(BaseModel):
    part_id: UUID
    quantity: int = Field(gt=0)
    price: Decimal = Field(gt=0, decimal_places=2)


class Order(BaseModel):
    model_config = ConfigDict(from_attributes=True, validate_assignment=True)

    id: UUID
    customer_id: UUID
    address: str = Field(min_length=1)
    items: list[OrderItem] = Field(min_length=1)
    status: OrderStatuses
    created_at: datetime

    @computed_field
    @property
    def total(self) -> Decimal:
        return sum((item.price * item.quantity for item in self.items), Decimal('0'))


class CreateOrderItem(BaseModel):
    part_id: UUID
    quantity: int = Field(gt=0)


class CreateOrderRequest(BaseModel):
    customer_id: UUID
    address: str = Field(min_length=1)
    items: list[CreateOrderItem] = Field(min_length=1)


class CancelOrderRequest(BaseModel):
    reason: str | None = None
