from datetime import datetime
from typing import Literal, Optional

from pydantic import Field

from app.models.base import MongoBaseModel


class FeedbackModel(MongoBaseModel):
    id: str = Field(alias="_id")
    user_id: str
    session_id: Optional[str] = None
    message_id: Optional[str] = None
    document_id: Optional[str] = None
    chunk_id: Optional[str] = None
    rating: Literal[-1, 0, 1]
    label: Optional[str] = None
    comment: Optional[str] = None
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)
