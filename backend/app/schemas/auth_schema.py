from pydantic import BaseModel, Field


class AuthRegisterRequest(BaseModel):
    name: str = Field(min_length=1)
    email: str
    password: str = Field(min_length=1)


class AuthLoginRequest(BaseModel):
    email: str
    password: str = Field(min_length=1)


class AuthUserResponse(BaseModel):
    id: str
    email: str
    name: str
    role: str = "user"


class AuthResponse(BaseModel):
    user: AuthUserResponse
    token: str
    token_type: str = "bearer"


class LogoutResponse(BaseModel):
    success: bool = True
