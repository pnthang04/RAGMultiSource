from pathlib import Path

from fastapi import UploadFile

from app.core.constants import (
    DOCUMENT_STATUS_UPLOADED,
    DOCUMENT_STATUS_READY,
    SOURCE_TYPE_USER_UPLOAD,
    VISIBILITY_PRIVATE,
)
from app.core.config import settings
from app.models.document import DocumentModel
from app.repositories.document_repository import DocumentRepository
from app.rag.pipeline.ingestion_pipeline import IngestionPipeline
from app.utils.file_utils import save_upload_file
from app.utils.id_utils import generate_id


class DocumentService:
    def __init__(self) -> None:
        self.document_repository = DocumentRepository()
        self.ingestion_pipeline = IngestionPipeline()

    async def upload_user_document(self, file: UploadFile, user_id: str, session_id: str | None):
        document_id = generate_id("doc")
        raw_path = str(Path(settings.UPLOAD_DIR) / f"{document_id}_{file.filename}")
        await save_upload_file(file, raw_path)
        file_size_bytes = Path(raw_path).stat().st_size
        document = DocumentModel(
            id=document_id,
            title=file.filename,
            filename=file.filename,
            file_type=(file.filename.split(".")[-1] if file.filename else "unknown"),
            mime_type=file.content_type or "application/octet-stream",
            source_type=SOURCE_TYPE_USER_UPLOAD,
            owner_user_id=user_id,
            uploaded_in_session_id=session_id,
            visibility=VISIBILITY_PRIVATE,
            raw_storage_path=raw_path,
            status=DOCUMENT_STATUS_UPLOADED,
            file_size_bytes=file_size_bytes,
        )
        await self.document_repository.create_document(document)
        await self.ingestion_pipeline.run(document)
        document.status = DOCUMENT_STATUS_READY
        return document

    async def list_documents(self, user_id: str):
        return await self.document_repository.list_user_documents(user_id)

    async def delete_document(self, document_id: str) -> None:
        await self.document_repository.delete_document(document_id)
