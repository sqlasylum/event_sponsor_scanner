from pydantic import BaseModel, EmailStr
from datetime import datetime


class LoginRequest(BaseModel):
    email: EmailStr
    next: str = "/"


class ScanRecord(BaseModel):
    id: int
    attendee_id: str
    sponsor_email: str
    scanned_at: datetime

    model_config = {"from_attributes": True}
