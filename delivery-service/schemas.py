from pydantic import BaseModel
from typing import Optional
from datetime import datetime
from enum import Enum

class DeliveryStatus(str, Enum):
    PENDING = "PENDING"
    DISPATCHED = "DISPATCHED"
    IN_TRANSIT = "IN_TRANSIT"
    DELIVERED = "DELIVERED"

# Base delivery schema
class DeliveryBase(BaseModel):
    order_uid: str
    delivery_person_id: Optional[int] = None
    status: Optional[DeliveryStatus] = DeliveryStatus.PENDING

# For creating a new delivery
class DeliveryCreate(BaseModel):
    order_uid: str
    status: Optional[DeliveryStatus] = DeliveryStatus.PENDING  # default to PENDING


# For updating status or delivery person
class DeliveryUpdate(BaseModel):
    status: Optional[DeliveryStatus]
    delivery_person_id: Optional[int]

# ✅ For PUT /delivery/update-status
class DeliveryStatusUpdateIn(BaseModel):
    delivery_uid: str
    status: DeliveryStatus


# ✅ For PUT /delivery/assign
class DeliveryAssignIn(BaseModel):
    delivery_uid: str
    delivery_person_id: int
    status: DeliveryStatus  # must be DISPATCHED ideally

# Response model
class DeliveryOut(BaseModel):
    id: int
    delivery_uid: str
    order_uid: str
    delivery_person_id: Optional[int]
    status: DeliveryStatus
    assigned_at: Optional[datetime]
    updated_at: datetime

    class Config:
        orm_mode = True
