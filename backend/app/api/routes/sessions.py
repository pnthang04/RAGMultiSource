from fastapi import APIRouter, Depends, HTTPException

from app.api.deps import get_current_user_id, get_session_service
from app.schemas.session_schema import SessionCreateRequest, SessionResponse, SessionUpdateRequest
from app.services.session_service import SessionService

router = APIRouter()


def _to_session_response(session: dict) -> SessionResponse:
    return SessionResponse(
        id=session["id"],
        owner_user_id=session["owner_user_id"],
        title=session.get("title"),
        description=session.get("description"),
        status=session.get("status", "active"),
        last_message_at=session.get("last_message_at"),
        created_at=session.get("created_at"),
        updated_at=session.get("updated_at"),
    )


@router.post("", response_model=SessionResponse)
async def create_session(
    payload: SessionCreateRequest,
    user_id: str = Depends(get_current_user_id),
    service: SessionService = Depends(get_session_service),
):
    session = await service.create_session(user_id=user_id, title=payload.title, description=payload.description)
    return _to_session_response(session.model_dump(by_alias=False))


@router.get("", response_model=list[SessionResponse])
async def list_sessions(
    user_id: str = Depends(get_current_user_id),
    service: SessionService = Depends(get_session_service),
):
    sessions = await service.list_sessions(user_id)
    return [_to_session_response(session) for session in sessions]


@router.get("/{session_id}", response_model=SessionResponse)
async def get_session(
    session_id: str,
    user_id: str = Depends(get_current_user_id),
    service: SessionService = Depends(get_session_service),
):
    session = await service.get_session(session_id, user_id)
    if session is None:
        raise HTTPException(status_code=404, detail="Session not found")
    return _to_session_response(session)


@router.patch("/{session_id}", response_model=SessionResponse)
async def update_session(
    session_id: str,
    payload: SessionUpdateRequest,
    user_id: str = Depends(get_current_user_id),
    service: SessionService = Depends(get_session_service),
):
    session = await service.update_session(
        session_id=session_id,
        user_id=user_id,
        title=payload.title,
        description=payload.description,
        status=payload.status,
    )
    if session is None:
        raise HTTPException(status_code=404, detail="Session not found")
    return _to_session_response(session)


@router.delete("/{session_id}")
async def delete_session(
    session_id: str,
    user_id: str = Depends(get_current_user_id),
    service: SessionService = Depends(get_session_service),
):
    deleted = await service.delete_session(session_id, user_id)
    if not deleted:
        raise HTTPException(status_code=404, detail="Session not found")
    return {"success": True, "session_id": session_id}
