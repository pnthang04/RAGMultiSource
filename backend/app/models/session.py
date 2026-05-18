from datetime import datetime
from typing import Literal, Optional

from pydantic import Field

from app.models.base import MongoBaseModel


class SessionModel(MongoBaseModel):
    id: str = Field(alias="_id")
    owner_user_id: str
    title: Optional[str] = None
    description: Optional[str] = None
    last_message_at: Optional[datetime] = None
    status: Literal["active", "archived", "deleted"] = "active"
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)
