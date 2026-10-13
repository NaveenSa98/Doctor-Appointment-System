"""Shared FastAPI dependencies: settings, clock, and the optional/required current user."""

from collections.abc import Callable
from datetime import datetime
from typing import Annotated

from fastapi import Depends, Request
from sqlalchemy.orm import Session

from app.core.clock import utcnow
from app.core.config import Settings
from app.core.errors import AppError, unauthorized
from app.core.ratelimit import enforce_rate_limit
from app.db.session import get_session
from app.models import User, UserRole
from app.services import auth_service


def get_app_settings(request: Request) -> Settings:
    """The settings the app was created with."""
    settings: Settings = request.app.state.settings
    return settings


def get_now() -> datetime:
    """The current UTC time. Tests override this to control the clock."""
    return utcnow()


SessionDep = Annotated[Session, Depends(get_session)]
SettingsDep = Annotated[Settings, Depends(get_app_settings)]
NowDep = Annotated[datetime, Depends(get_now)]


def get_optional_user(
    request: Request, session: SessionDep, settings: SettingsDep, now: NowDep
) -> User | None:
    """Return the signed-in user, or None when no Authorization header is sent.

    A header that is present but invalid or expired is a 401, never treated as anonymous.
    """
    header = request.headers.get("authorization")
    if header is None:
        return None
    scheme, _, token = header.partition(" ")
    if scheme.lower() != "bearer" or not token.strip():
        raise unauthorized("Invalid Authorization header")
    return auth_service.user_from_token(session, settings, token.strip(), now)


def get_current_user(user: Annotated[User | None, Depends(get_optional_user)]) -> User:
    """Require a signed-in user."""
    if user is None:
        raise unauthorized()
    return user


CurrentUser = Annotated[User, Depends(get_current_user)]


def require_role(*roles: UserRole) -> Callable[[User], User]:
    """Build a dependency that only lets the given roles through (403 otherwise)."""

    def checker(user: CurrentUser) -> User:
        if user.role not in roles:
            raise AppError(403, "forbidden", "You do not have access to this resource")
        return user

    return checker


def login_rate_limit(request: Request, settings: SettingsDep) -> None:
    """Limit login attempts per client."""
    enforce_rate_limit(request, "login", settings.login_rate_limit_per_minute)


def booking_rate_limit(
    request: Request,
    settings: SettingsDep,
    user: Annotated[User | None, Depends(get_optional_user)],
) -> None:
    """Limit anonymous bookings per client. Signed-in staff are not limited."""
    if user is None:
        enforce_rate_limit(request, "booking", settings.booking_rate_limit_per_minute)
