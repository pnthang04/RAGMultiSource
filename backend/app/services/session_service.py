from typing import Any

from app.models.session import SessionModel
from app.repositories.message_repository import MessageRepository
from app.repositories.session_repository import SessionRepository
from app.utils.id_utils import generate_id


class SessionService:
    def __init__(self) -> None:
        self.session_repository = SessionRepository()
        self.message_repository = MessageRepository()

    def _serialize_session(self, session: dict[str, Any]) -> dict[str, Any]:
        return {
            "id": session.get("_id"),
            "owner_user_id": session.get("owner_user_id"),
            "title": session.get("title"),
            "description": session.get("description"),
            "status": session.get("status", "active"),
            "last_message_at": session.get("last_message_at"),
            "created_at": session.get("created_at"),
            "updated_at": session.get("updated_at"),
        }

    async def create_session(self, user_id: str, title: str | None = None, description: str | None = None) -> SessionModel:
        session = SessionModel(id=generate_id("sess"), owner_user_id=user_id, title=title, description=description)
        await self.session_repository.create_session(session)
        return session

    async def list_sessions(self, user_id: str):
        sessions = await self.session_repository.list_user_sessions(user_id)
        return [self._serialize_session(session) for session in sessions]

    async def get_session(self, session_id: str, user_id: str) -> dict[str, Any] | None:
        session = await self.session_repository.get_session_by_id(session_id)
        if session is None or session.get("owner_user_id") != user_id:
            return None
        return self._serialize_session(session)

    async def update_session(
        self,
        session_id: str,
        user_id: str,
        title: str | None = None,
        description: str | None = None,
        status: str | None = None,
    ) -> dict[str, Any] | None:
        session = await self.session_repository.get_session_by_id(session_id)
        if session is None or session.get("owner_user_id") != user_id:
            return None
        fields: dict[str, Any] = {}
        if title is not None:
            fields["title"] = title
        if description is not None:
            fields["description"] = description
        if status is not None:
            fields["status"] = status
        await self.session_repository.update_session(session_id, **fields)
        updated = await self.session_repository.get_session_by_id(session_id)
        return self._serialize_session(updated) if updated else None

    async def delete_session(self, session_id: str, user_id: str) -> bool:
        session = await self.session_repository.get_session_by_id(session_id)
        if session is None or session.get("owner_user_id") != user_id:
            return False
        await self.message_repository.delete_session_messages(session_id)
        return await self.session_repository.delete_session(session_id)

    async def list_session_messages(self, session_id: str, user_id: str):
        session = await self.session_repository.get_session_by_id(session_id)
        if session is None or session.get("owner_user_id") != user_id:
            return None
        return await self.message_repository.list_session_messages(session_id)

    async def touch_session(self, session_id: str) -> None:
        await self.session_repository.touch_session(session_id)
