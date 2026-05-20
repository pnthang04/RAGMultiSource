from fastapi import APIRouter, Depends, HTTPException

from app.api.deps import get_current_user_id, get_session_service
from app.services.session_service import SessionService

router = APIRouter()


@router.get("/sessions/{session_id}/messages")
async def list_session_messages(
    session_id: str,
    user_id: str = Depends(get_current_user_id),
    service: SessionService = Depends(get_session_service),
):
    messages = await service.list_session_messages(session_id, user_id)
    if messages is None:
        raise HTTPException(status_code=404, detail="Session not found")
    return messages
