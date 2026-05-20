from datetime import datetime
from typing import Any, Optional

from pydantic import BaseModel, Field


class SourceItem(BaseModel):
    document_id: str
    chunk_id: str
    filename: str
    source_type: str
    procedure_title: Optional[str] = None
    page_number: Optional[int] = None
    page_source: Optional[str] = None
    section_title: Optional[str] = None
    score: Optional[float] = None
    visibility: Optional[str] = None
    owner_user_id: Optional[str] = None
    session_id: Optional[str] = None


class BaseResponse(BaseModel):
    success: bool = True
    detail: Optional[str] = None


class TimestampedItem(BaseModel):
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)


class MetadataPayload(BaseModel):
    metadata: dict[str, Any] = Field(default_factory=dict)
