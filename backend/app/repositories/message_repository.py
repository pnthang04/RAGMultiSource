from typing import Any

from app.db.mongodb import get_database
from app.models.message import MessageModel


class MessageRepository:
    collection_name = "messages"

    def _collection(self):
        return get_database()[self.collection_name]

    async def create_message(self, message: MessageModel) -> str:
        await self._collection().insert_one(message.model_dump(by_alias=True))
        return message.id

    async def list_session_messages(self, session_id: str) -> list[dict[str, Any]]:
        cursor = self._collection().find({"session_id": session_id}).sort("created_at", 1)
        return [message async for message in cursor]

    async def delete_session_messages(self, session_id: str) -> int:
        result = await self._collection().delete_many({"session_id": session_id})
        return result.deleted_count
