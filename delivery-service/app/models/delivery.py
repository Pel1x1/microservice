import enum
from uuid import UUID
from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field


class DeliveryStatuses(enum.Enum):
    ASSIGNED = 'assigned'        # доставка назначена, посылка ждёт передачи службе доставки
    IN_TRANSIT = 'in_transit'    # посылка передана службе доставки и едет к покупателю
    DELIVERED = 'delivered'      # посылка доставлена


class Delivery(BaseModel):
    """Доставка собранного заказа."""
    model_config = ConfigDict(from_attributes=True, validate_assignment=True)

    id: UUID
    order_id: UUID
    address: str = Field(min_length=1)
    status: DeliveryStatuses = DeliveryStatuses.ASSIGNED
    created_at: datetime
