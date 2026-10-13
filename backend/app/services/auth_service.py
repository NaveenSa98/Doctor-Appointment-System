"""Login and token-to-user resolution."""

from datetime import datetime, timedelta

from sqlalchemy.orm import Session

from app.core.config import Settings
from app.core.errors import AppError, unauthorized
from app.core.security import (
    TokenError,
    burn_password_check,
    create_access_token,
    decode_access_token,
    verify_password,
)
from app.models import User
from app.repositories import user_repository
from app.schemas.auth import LoginResponse, UserOut


def _invalid_credentials() -> AppError:
    # One response for unknown email, wrong password and disabled account.
    return AppError(401, "invalid_credentials", "Incorrect email or password")


def login(
    session: Session, settings: Settings, email: str, password: str, now: datetime
) -> LoginResponse:
    """Check credentials and issue an access token."""
    user = user_repository.get_by_email(session, email)
    if user is None:
        burn_password_check(password)
        raise _invalid_credentials()
    if not verify_password(password, user.password_hash) or not user.is_active:
        raise _invalid_credentials()

    lifetime = timedelta(minutes=settings.access_token_minutes)
    token = create_access_token(user.id, user.role.value, settings.jwt_secret, now, lifetime)
    return LoginResponse(
        access_token=token,
        expires_in=int(lifetime.total_seconds()),
        user=UserOut.model_validate(user),
    )


def user_from_token(session: Session, settings: Settings, token: str, now: datetime) -> User:
    """Resolve a bearer token to an active user, or raise 401."""
    try:
        payload = decode_access_token(token, settings.jwt_secret, now)
    except TokenError as exc:
        raise unauthorized("Invalid or expired token") from exc
    user = user_repository.get_by_id(session, payload.user_id)
    if user is None or not user.is_active:
        raise unauthorized("Invalid or expired token")
    return user
