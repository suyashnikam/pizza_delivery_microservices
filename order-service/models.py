from sqlalchemy import Column, Integer, String, Float, ForeignKey, DateTime, Enum as SqlEnum, Text
from sqlalchemy.orm import relationship
from datetime import datetime
from enum import Enum
from database import Base
import uuid


class OrderStatus(str, Enum):
    PENDING = "PENDING"
    CONFIRMED = "CONFIRMED"
    PREPARING = "PREPARING"
    OUT_FOR_DELIVERY = "OUT_FOR_DELIVERY"
    DELIVERED = "DELIVERED"
    CANCELLED = "CANCELLED"


class Order(Base):
    __tablename__ = "orders"

    id = Column(Integer, primary_key=True, index=True)
    customer_id = Column(Integer, nullable=False)
    outlet_code = Column(String, nullable=False)
    total_price = Column(Float, nullable=False)
    status = Column(SqlEnum(OrderStatus), default=OrderStatus.PENDING)
    created_at = Column(DateTime, default=datetime.utcnow)
    order_uid = Column(String, unique=True, index=True, default=lambda: str(uuid.uuid4()))
    delivery_address = Column(Text, nullable=True)

    items = relationship("OrderItem", back_populates="order", cascade="all, delete-orphan")


class OrderItem(Base):
    __tablename__ = "order_items"

    id = Column(Integer, primary_key=True, index=True)
    order_id = Column(Integer, ForeignKey("orders.id"))

    # Pizza ID from menu-service
    pizza_id = Column(Integer, nullable=False)
    quantity = Column(Integer, nullable=False)
    price = Column(Float, nullable=False)

    order = relationship("Order", back_populates="items")
