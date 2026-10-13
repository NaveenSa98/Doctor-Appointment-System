"""Authentication endpoints."""

from fastapi import APIRouter, Depends

from app.api.v1.deps import CurrentUser, NowDep, SessionDep, SettingsDep, login_rate_limit
from app.models import User
from app.schemas.auth import LoginRequest, LoginResponse, UserOut
from app.services import auth_service

router = APIRouter(prefix="/auth", tags=["auth"])


@router.post("/login", response_model=LoginResponse, dependencies=[Depends(login_rate_limit)])
def login(
    body: LoginRequest, session: SessionDep, settings: SettingsDep, now: NowDep
) -> LoginResponse:
    """Exchange an email and password for a bearer token."""
    return auth_service.login(session, settings, body.email, body.password, now)


@router.get("/me", response_model=UserOut)
def me(user: CurrentUser) -> User:
    """Return the signed-in user."""
    return user
