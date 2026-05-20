from datetime import datetime
from typing import Literal, Optional

from pydantic import Field

from app.models.base import MongoBaseModel


class UserModel(MongoBaseModel):
    id: str = Field(alias="_id")
    email: str
    name: str
    role: Literal["user", "admin"] = "user"
    password_hash: Optional[str] = None
    password_salt: Optional[str] = None
    auth_token: Optional[str] = None
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)
