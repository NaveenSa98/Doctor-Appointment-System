"""Authentication and account endpoints."""

from fastapi import APIRouter, Depends, Response

from app.api.v1.deps import (
    CurrentUser,
    NowDep,
    SessionDep,
    SettingsDep,
    login_rate_limit,
    register_rate_limit,
)
from app.models import User
from app.schemas.auth import (
    DeleteAccountRequest,
    LoginRequest,
    LoginResponse,
    ProfileUpdate,
    RegisterRequest,
    UserOut,
)
from app.services import auth_service

router = APIRouter(prefix="/auth", tags=["auth"])


@router.post("/login", response_model=LoginResponse, dependencies=[Depends(login_rate_limit)])
def login(
    body: LoginRequest, session: SessionDep, settings: SettingsDep, now: NowDep
) -> LoginResponse:
    """Exchange an email and password for a bearer token."""
    return auth_service.login(session, settings, body.email, body.password, now)


@router.post(
    "/register",
    response_model=LoginResponse,
    status_code=201,
    dependencies=[Depends(register_rate_limit)],
)
def register(
    body: RegisterRequest, session: SessionDep, settings: SettingsDep, now: NowDep
) -> LoginResponse:
    """Create a patient account and sign it in."""
    return auth_service.register(session, settings, body, now)


@router.get("/me", response_model=UserOut)
def me(user: CurrentUser) -> User:
    """Return the signed-in user."""
    return user


@router.patch("/me", response_model=UserOut)
def update_me(body: ProfileUpdate, session: SessionDep, user: CurrentUser) -> User:
    """Change your name, email or password."""
    return auth_service.update_profile(session, user, body)


@router.delete("/me", status_code=204, response_class=Response)
def delete_me(body: DeleteAccountRequest, session: SessionDep, user: CurrentUser) -> Response:
    """Delete your own (patient) account. Your past bookings are kept."""
    auth_service.delete_account(session, user, body.password)
    return Response(status_code=204)
