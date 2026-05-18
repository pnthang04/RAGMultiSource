from app.services.chat_service import ChatService
from app.services.document_service import DocumentService
from app.services.session_service import SessionService
from app.services.system_document_service import SystemDocumentService
from app.services.user_service import UserService


def get_current_user_id() -> str:
    return "demo_user_001"


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
