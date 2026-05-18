from typing import Optional

from pydantic import BaseModel


class SessionCreateRequest(BaseModel):
    title: Optional[str] = None
    description: Optional[str] = None


class SessionResponse(BaseModel):
    id: str
    owner_user_id: str
    title: Optional[str] = None
    description: Optional[str] = None
    status: str = "active"
