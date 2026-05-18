from datetime import datetime
from typing import Literal

from pydantic import Field

from app.models.base import MongoBaseModel


class UserModel(MongoBaseModel):
    id: str = Field(alias="_id")
    email: str
    name: str
    role: Literal["user", "admin"] = "user"
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)
