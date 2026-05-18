from fastapi import APIRouter, Depends

from app.api.deps import get_current_user_id, get_session_service
from app.schemas.session_schema import SessionCreateRequest, SessionResponse
from app.services.session_service import SessionService

router = APIRouter()


@router.post("", response_model=SessionResponse)
async def create_session(
    payload: SessionCreateRequest,
    user_id: str = Depends(get_current_user_id),
    service: SessionService = Depends(get_session_service),
):
    session = await service.create_session(user_id=user_id, title=payload.title, description=payload.description)
    return SessionResponse(
        id=session.id,
        owner_user_id=session.owner_user_id,
        title=session.title,
        description=session.description,
        status=session.status,
    )


@router.get("")
async def list_sessions(
    user_id: str = Depends(get_current_user_id),
    service: SessionService = Depends(get_session_service),
):
    return await service.list_sessions(user_id)
