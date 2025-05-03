from pydantic import BaseModel, Field
from typing import Optional
from datetime import time

# --- Schema to create a new outlet ---
class OutletCreate(BaseModel):
    name: str = Field(..., example="Pizza Hub - Pune")
    address: str = Field(..., example="123 MG Road, Pune")
    pincode: str = Field(..., example="411001")
    contact_number: Optional[str] = Field(None, example="9876543210")
    open_time: Optional[time] = Field(None, example="10:00")
    close_time: Optional[time] = Field(None, example="22:00")
    is_active: bool = Field(default=True)
    code: str = Field(..., example="OUTLET_PUNE_001")

# --- Schema for API response (includes ID) ---
class OutletOut(OutletCreate):
    id: int

    class Config:
        orm_mode = True
