from datetime import datetime

from app.core.security import generate_token, hash_password, verify_password
from app.models.user import UserModel
from app.repositories.user_repository import UserRepository
from app.utils.id_utils import generate_id


class UserService:
    def __init__(self) -> None:
        self.user_repository = UserRepository()

    def get_demo_user(self) -> UserModel:
        return UserModel(id="demo_user_001", email="demo@example.com", name="Demo User")

    def _serialize_user(self, user: dict) -> UserModel:
        return UserModel(
            id=user["_id"],
            email=user["email"],
            name=user["name"],
            role=user.get("role", "user"),
            password_hash=user.get("password_hash"),
            password_salt=user.get("password_salt"),
            auth_token=user.get("auth_token"),
            created_at=user.get("created_at", datetime.utcnow()),
            updated_at=user.get("updated_at", datetime.utcnow()),
        )

    async def register_user(self, name: str, email: str, password: str) -> tuple[UserModel, str]:
        normalized_email = email.strip().lower()
        normalized_name = name.strip()
        if not normalized_name:
            raise ValueError("Name is required.")
        if not normalized_email or not password:
            raise ValueError("Email and password are required.")
        existing = await self.user_repository.get_user_by_email(normalized_email)
        if existing is not None:
            raise ValueError("Email already exists.")

        password_hash, password_salt = hash_password(password)
        token = generate_token()
        user = UserModel(
            id=generate_id("usr"),
            email=normalized_email,
            name=normalized_name,
            password_hash=password_hash,
            password_salt=password_salt,
            auth_token=token,
        )
        await self.user_repository.create_user(user)
        return user, token

    async def login_user(self, email: str, password: str) -> tuple[UserModel, str]:
        normalized_email = email.strip().lower()
        user_doc = await self.user_repository.get_user_by_email(normalized_email)
        if user_doc is None:
            raise ValueError("Invalid email or password.")
        password_hash = user_doc.get("password_hash")
        password_salt = user_doc.get("password_salt")
        if not password_hash or not password_salt or not verify_password(password, password_hash, password_salt):
            raise ValueError("Invalid email or password.")
        token = generate_token()
        await self.user_repository.update_auth_token(user_doc["_id"], token)
        user_doc["auth_token"] = token
        return self._serialize_user(user_doc), token

    async def get_user_by_token(self, token: str) -> UserModel | None:
        user_doc = await self.user_repository.get_user_by_token(token)
        if user_doc is None:
            return None
        return self._serialize_user(user_doc)

    async def logout_user(self, token: str) -> None:
        user_doc = await self.user_repository.get_user_by_token(token)
        if user_doc is None:
            return
        await self.user_repository.update_auth_token(user_doc["_id"], None)
