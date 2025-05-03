# utils/timezone.py
from datetime import datetime
import pytz

def to_ist(utc_dt: datetime) -> str:
    """Convert UTC datetime to IST formatted string"""
    ist = pytz.timezone("Asia/Kolkata")
    return utc_dt.astimezone(ist).strftime("%Y-%m-%d %H:%M:%S")
