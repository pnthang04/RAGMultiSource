from datetime import datetime
from typing import Any, Literal, Optional

from pydantic import Field

from app.models.base import MongoBaseModel


class EmbeddingMetadata(MongoBaseModel):
    model: str
    dimension: int
    vector_store: str = "chroma"
    collection_name: str = "rag_chunks"
    vector_id: str
    embedded_at: Optional[datetime] = None


class ChunkModel(MongoBaseModel):
    id: str = Field(alias="_id")
    document_id: str
    document_version_id: Optional[str] = None
    chunk_index: int
    content: str
    source_type: Literal["system", "user_upload"]
    visibility: Literal["global", "private"]
    owner_user_id: Optional[str] = None
    session_id: Optional[str] = None
    filename: str
    procedure_title: Optional[str] = None
    file_type: Optional[str] = None
    page_start: Optional[int] = None
    page_end: Optional[int] = None
    page_source: Optional[str] = None
    section_title: Optional[str] = None
    heading_path: list[str] = Field(default_factory=list)
    token_count: int = 0
    char_start: Optional[int] = None
    char_end: Optional[int] = None
    chunk_type: Literal["text", "table", "image", "mixed"] = "text"
    contains_table: bool = False
    contains_image: bool = False
    language: str = "vi"
    content_hash: Optional[str] = None
    table_metadata: dict[str, Any] = Field(default_factory=dict)
    embedding: EmbeddingMetadata = Field(default_factory=lambda: EmbeddingMetadata(model="", dimension=0, vector_id=""))
    metadata: dict[str, Any] = Field(default_factory=dict)
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)
