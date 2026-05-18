from app.models.user import UserModel


class UserService:
    def get_demo_user(self) -> UserModel:
        return UserModel(id="demo_user_001", email="demo@example.com", name="Demo User")
