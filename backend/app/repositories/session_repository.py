from datetime import datetime
from typing import Any, Optional

from app.db.mongodb import get_database
from app.models.session import SessionModel


class SessionRepository:
    collection_name = "sessions"

    def _collection(self):
        return get_database()[self.collection_name]

    async def create_session(self, session: SessionModel) -> str:
        await self._collection().insert_one(session.model_dump(by_alias=True))
        return session.id

    async def get_session_by_id(self, session_id: str) -> Optional[dict[str, Any]]:
        return await self._collection().find_one({"_id": session_id})

    async def list_user_sessions(self, user_id: str) -> list[dict[str, Any]]:
        cursor = self._collection().find({"owner_user_id": user_id}).sort([("last_message_at", -1), ("updated_at", -1)])
        return [session async for session in cursor]

    async def update_session(self, session_id: str, **fields: Any) -> bool:
        payload = dict(fields)
        payload["updated_at"] = datetime.utcnow()
        result = await self._collection().update_one({"_id": session_id}, {"$set": payload})
        return result.modified_count > 0

    async def delete_session(self, session_id: str) -> bool:
        result = await self._collection().delete_one({"_id": session_id})
        return result.deleted_count > 0

    async def touch_session(self, session_id: str) -> None:
        now = datetime.utcnow()
        await self._collection().update_one(
            {"_id": session_id},
            {"$set": {"last_message_at": now, "updated_at": now}},
        )
