from typing import Any, Optional

from pydantic import BaseModel, Field

from app.schemas.common_schema import SourceItem


class ChatRequest(BaseModel):
    question: str
    session_id: Optional[str] = None
    scope: str = "auto"
    selected_document_ids: list[str] = Field(default_factory=list)


class ChatResponse(BaseModel):
    answer: str
    sources: list[SourceItem] = Field(default_factory=list)
    raw_contexts: list[dict[str, Any]] = Field(default_factory=list)
