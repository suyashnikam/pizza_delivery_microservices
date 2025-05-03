from pydantic import BaseModel
from typing import List, Optional
from enum import Enum

class OrderStatus(str, Enum):
    PENDING = "PENDING"
    CONFIRMED = "CONFIRMED"
    PREPARING = "PREPARING"
    OUT_FOR_DELIVERY = "OUT_FOR_DELIVERY"
    DELIVERED = "DELIVERED"
    CANCELLED = "CANCELLED"

# Input from user to place an order
class OrderItemInput(BaseModel):
    pizza_id: int
    quantity: int

class OrderCreate(BaseModel):
    outlet_code: str
    items: List[OrderItemInput]
    delivery_address: Optional[str] = None

# Output to show order items with price details
class OrderItemOut(BaseModel):
    pizza_id: int
    quantity: int
    unit_price: float
    subtotal: float

    class Config:
        orm_mode = True

# Final response after placing order
class OrderOut(BaseModel):
    id: int
    customer_id: int
    outlet_code: str
    total_price: float
    status: OrderStatus
    created_at: str  # in IST format
    items: List[OrderItemOut]
    order_uid: str
    delivery_address: Optional[str] = None

    class Config:
        orm_mode = True


class UpdateOrderStatus(BaseModel):
    new_status: OrderStatus

