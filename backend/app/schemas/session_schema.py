from datetime import datetime
from typing import Optional

from pydantic import BaseModel


class SessionCreateRequest(BaseModel):
    title: Optional[str] = None
    description: Optional[str] = None


class SessionUpdateRequest(BaseModel):
    title: Optional[str] = None
    description: Optional[str] = None
    status: Optional[str] = None


class SessionResponse(BaseModel):
    id: str
    owner_user_id: str
    title: Optional[str] = None
    description: Optional[str] = None
    status: str = "active"
    last_message_at: Optional[datetime] = None
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None
