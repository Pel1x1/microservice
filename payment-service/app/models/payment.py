import enum
from uuid import UUID
from decimal import Decimal
from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field


class PaymentStatuses(enum.Enum):
    PENDING = 'pending'        # ждёт оплаты
    CONFIRMED = 'confirmed'    # оплата подтверждена эквайрингом
    FAILED = 'failed'          # оплата не прошла или заказ отменён до оплаты
    REFUNDED = 'refunded'      # деньги возвращены покупателю


class Payment(BaseModel):
    """Оплата заказа."""
    model_config = ConfigDict(from_attributes=True, validate_assignment=True)

    id: UUID
    order_id: UUID
    amount: Decimal = Field(gt=0, decimal_places=2)
    status: PaymentStatuses = PaymentStatuses.PENDING
    created_at: datetime
