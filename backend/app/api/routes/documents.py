from fastapi import APIRouter, Depends, File, Query, UploadFile

from app.api.deps import get_current_user_id, get_document_service
from app.schemas.document_schema import DocumentUploadResponse
from app.services.document_service import DocumentService

router = APIRouter()


@router.post("/upload", response_model=DocumentUploadResponse)
async def upload_document(
    file: UploadFile = File(...),
    session_id: str | None = Query(default=None),
    user_id: str = Depends(get_current_user_id),
    service: DocumentService = Depends(get_document_service),
):
    document = await service.upload_user_document(file=file, user_id=user_id, session_id=session_id)
    return DocumentUploadResponse(
        document_id=document.id,
        filename=document.filename,
        status=document.status,
        message="Document uploaded and ingested",
    )


@router.get("")
async def list_documents(
    user_id: str = Depends(get_current_user_id),
    service: DocumentService = Depends(get_document_service),
):
    return await service.list_documents(user_id)


@router.delete("/{document_id}")
async def delete_document(
    document_id: str,
    service: DocumentService = Depends(get_document_service),
):
    await service.delete_document(document_id)
    return {"success": True}
