from datetime import datetime
from typing import Any, Optional

from app.db.mongodb import get_database
from app.models.user import UserModel


class UserRepository:
    collection_name = "users"

    def _collection(self):
        return get_database()[self.collection_name]

    async def create_user(self, user: UserModel) -> str:
        await self._collection().insert_one(user.model_dump(by_alias=True))
        return user.id

    async def get_user_by_id(self, user_id: str) -> Optional[dict[str, Any]]:
        return await self._collection().find_one({"_id": user_id})

    async def get_user_by_email(self, email: str) -> Optional[dict[str, Any]]:
        return await self._collection().find_one({"email": email.lower().strip()})

    async def get_user_by_token(self, token: str) -> Optional[dict[str, Any]]:
        return await self._collection().find_one({"auth_token": token})

    async def update_auth_token(self, user_id: str, token: str | None) -> None:
        await self._collection().update_one(
            {"_id": user_id},
            {"$set": {"auth_token": token, "updated_at": datetime.utcnow()}},
        )

    async def update_user_fields(self, user_id: str, **fields: Any) -> None:
        payload = dict(fields)
        payload["updated_at"] = datetime.utcnow()
        await self._collection().update_one({"_id": user_id}, {"$set": payload})
