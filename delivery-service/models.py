from sqlalchemy import Column, Integer, String, DateTime, Enum
from datetime import datetime
from database import Base
import enum
import uuid

class DeliveryStatus(str, enum.Enum):
    PENDING = "PENDING"
    DISPATCHED = "DISPATCHED"
    IN_TRANSIT = "IN_TRANSIT"
    DELIVERED = "DELIVERED"


class Delivery(Base):
    __tablename__ = "deliveries"

    id = Column(Integer, primary_key=True, index=True)
    order_uid = Column(String, unique=True, nullable=False)
    delivery_person_id = Column(Integer, nullable=True)  # Links to delivery user via external call
    delivery_uid = Column(String, unique=True, default=lambda: str(uuid.uuid4()), nullable=False)
    status = Column(Enum(DeliveryStatus), default=DeliveryStatus.PENDING)
    assigned_at = Column(DateTime, nullable=True)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
