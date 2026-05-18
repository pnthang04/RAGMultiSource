from fastapi import UploadFile

from pathlib import Path

from app.core.config import settings
from app.core.constants import DOCUMENT_STATUS_READY, DOCUMENT_STATUS_UPLOADED, SOURCE_TYPE_SYSTEM, VISIBILITY_GLOBAL
from app.models.document import DocumentModel
from app.repositories.document_repository import DocumentRepository
from app.rag.pipeline.ingestion_pipeline import IngestionPipeline
from app.utils.file_utils import save_upload_file
from app.utils.id_utils import generate_id


class SystemDocumentService:
    def __init__(self) -> None:
        self.document_repository = DocumentRepository()
        self.ingestion_pipeline = IngestionPipeline()

    async def upload_system_document(self, file: UploadFile):
        document_id = generate_id("sysdoc")
        raw_path = str(Path(settings.UPLOAD_DIR) / f"{document_id}_{file.filename}")
        await save_upload_file(file, raw_path)
        file_size_bytes = Path(raw_path).stat().st_size
        document = DocumentModel(
            id=document_id,
            title=file.filename,
            filename=file.filename,
            file_type=(file.filename.split(".")[-1] if file.filename else "unknown"),
            mime_type=file.content_type or "application/octet-stream",
            source_type=SOURCE_TYPE_SYSTEM,
            owner_user_id=None,
            uploaded_in_session_id=None,
            visibility=VISIBILITY_GLOBAL,
            raw_storage_path=raw_path,
            status=DOCUMENT_STATUS_UPLOADED,
            file_size_bytes=file_size_bytes,
        )
        await self.document_repository.create_document(document)
        await self.ingestion_pipeline.run(document)
        document.status = DOCUMENT_STATUS_READY
        return document
