from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer

from app.api.deps import get_current_user, get_user_service
from app.schemas.auth_schema import (
    AuthLoginRequest,
    AuthRegisterRequest,
    AuthResponse,
    AuthUserResponse,
    LogoutResponse,
)
from app.services.user_service import UserService

router = APIRouter()
bearer_scheme = HTTPBearer(auto_error=False)


def to_auth_user_response(user) -> AuthUserResponse:
    return AuthUserResponse(id=user.id, email=user.email, name=user.name, role=user.role)


@router.post("/register", response_model=AuthResponse)
async def register(
    payload: AuthRegisterRequest,
    service: UserService = Depends(get_user_service),
):
    try:
        user, token = await service.register_user(payload.name, payload.email, payload.password)
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc
    return AuthResponse(user=to_auth_user_response(user), token=token)


@router.post("/login", response_model=AuthResponse)
async def login(
    payload: AuthLoginRequest,
    service: UserService = Depends(get_user_service),
):
    try:
        user, token = await service.login_user(payload.email, payload.password)
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail=str(exc)) from exc
    return AuthResponse(user=to_auth_user_response(user), token=token)


@router.get("/me", response_model=AuthUserResponse)
async def me(current_user=Depends(get_current_user)):
    return to_auth_user_response(current_user)


@router.post("/logout", response_model=LogoutResponse)
async def logout(
    credentials: HTTPAuthorizationCredentials | None = Depends(bearer_scheme),
    service: UserService = Depends(get_user_service),
):
    if credentials is not None and credentials.credentials:
        await service.logout_user(credentials.credentials)
    return LogoutResponse(success=True)
