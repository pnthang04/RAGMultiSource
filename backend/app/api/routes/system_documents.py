from fastapi import APIRouter, Depends, File, UploadFile

from app.api.deps import get_system_document_service
from app.schemas.document_schema import DocumentUploadResponse
from app.services.system_document_service import SystemDocumentService

router = APIRouter()


@router.post("/upload", response_model=DocumentUploadResponse)
async def upload_system_document(
    file: UploadFile = File(...),
    service: SystemDocumentService = Depends(get_system_document_service),
):
    document = await service.upload_system_document(file=file)
    return DocumentUploadResponse(
        document_id=document.id,
        filename=document.filename,
        status=document.status,
        message="System document uploaded and ingested",
    )
