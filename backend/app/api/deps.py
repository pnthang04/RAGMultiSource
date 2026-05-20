from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer

from app.models.user import UserModel
from app.services.chat_service import ChatService
from app.services.document_service import DocumentService
from app.services.session_service import SessionService
from app.services.system_document_service import SystemDocumentService
from app.services.user_service import UserService

bearer_scheme = HTTPBearer(auto_error=False)


async def get_current_user(
    credentials: HTTPAuthorizationCredentials | None = Depends(bearer_scheme),
    service: UserService = Depends(get_user_service),
) -> UserModel:
    if credentials is None or not credentials.credentials:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Unauthorized")
    user = await service.get_user_by_token(credentials.credentials)
    if user is None:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid token")
    return user


async def get_current_user_id(current_user: UserModel = Depends(get_current_user)) -> str:
    return current_user.id


def get_document_service() -> DocumentService:
    return DocumentService()


def get_system_document_service() -> SystemDocumentService:
    return SystemDocumentService()


def get_session_service() -> SessionService:
    return SessionService()


def get_chat_service() -> ChatService:
    return ChatService()


def get_user_service() -> UserService:
    return UserService()
