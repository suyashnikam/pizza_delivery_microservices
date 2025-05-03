from sqlalchemy import Column, Integer, String, Boolean, Time
from database import Base

class Outlet(Base):
    __tablename__ = "outlets"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, nullable=False)
    address = Column(String, nullable=False)
    pincode = Column(String, nullable=False)
    contact_number = Column(String, nullable=True)
    open_time = Column(Time, nullable=True)
    close_time = Column(Time, nullable=True)
    is_active = Column(Boolean, default=True)
    code = Column(String, unique=True, nullable=False, index=True)
