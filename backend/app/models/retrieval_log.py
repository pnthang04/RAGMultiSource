from datetime import datetime
from typing import Any, Literal, Optional

from pydantic import Field

from app.models.base import MongoBaseModel


class RetrievalLogModel(MongoBaseModel):
    id: str = Field(alias="_id")
    user_id: str
    session_id: Optional[str] = None
    question: str
    resolved_scope: Literal["current_upload", "all_user_uploads", "system_docs", "mixed", "auto"]
    selected_document_ids: list[str] = Field(default_factory=list)
    retrieval_filter: dict[str, Any] = Field(default_factory=dict)
    top_k: int = 5
    retrieved_chunk_ids: list[str] = Field(default_factory=list)
    response_metadata: dict[str, Any] = Field(default_factory=dict)
    created_at: datetime = Field(default_factory=datetime.utcnow)
