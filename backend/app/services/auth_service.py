"""Login and token-to-user resolution."""

from datetime import datetime, timedelta

from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.core.config import Settings
from app.core.errors import AppError, ForbiddenError, ValidationFailed, unauthorized
from app.core.security import (
    TokenError,
    burn_password_check,
    create_access_token,
    decode_access_token,
    hash_password,
    verify_password,
)
from app.models import User, UserRole
from app.repositories import user_repository
from app.schemas.auth import LoginResponse, ProfileUpdate, RegisterRequest, UserOut


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

    return _issue_token(settings, user, now)


def _issue_token(settings: Settings, user: User, now: datetime) -> LoginResponse:
    lifetime = timedelta(minutes=settings.access_token_minutes)
    token = create_access_token(user.id, user.role.value, settings.jwt_secret, now, lifetime)
    return LoginResponse(
        access_token=token,
        expires_in=int(lifetime.total_seconds()),
        user=UserOut.model_validate(user),
    )


def _email_taken() -> AppError:
    return AppError(409, "email_taken", "An account with this email already exists")


def _save_user(session: Session, user: User) -> None:
    """Write the user; the unique email index settles a race between two sign-ups."""
    try:
        with session.begin_nested():
            user_repository.add(session, user)
    except IntegrityError as exc:
        raise _email_taken() from exc


def register(
    session: Session, settings: Settings, data: RegisterRequest, now: datetime
) -> LoginResponse:
    """Create a patient account and sign it in. The role is never taken from the request."""
    if user_repository.get_by_email(session, data.email) is not None:
        raise _email_taken()
    user = User(
        email=data.email,
        full_name=data.full_name,
        password_hash=hash_password(data.password),
        role=UserRole.PATIENT,
    )
    _save_user(session, user)
    session.commit()
    return _issue_token(settings, user, now)


def _require_current_password(user: User, password: str | None) -> None:
    if not password or not verify_password(password, user.password_hash):
        # A 422 on the field, not a 401: a 401 would sign the person out in the app.
        raise ValidationFailed("current_password", "is incorrect")


def update_profile(session: Session, user: User, data: ProfileUpdate) -> User:
    """Change the name, email or password of the signed-in user."""
    changes = data.model_fields_set
    if "email" in changes or "new_password" in changes:
        _require_current_password(user, data.current_password)
    if data.full_name is not None:
        user.full_name = data.full_name
    if data.new_password is not None:
        user.password_hash = hash_password(data.new_password)
    if data.email is not None and data.email.lower() != user.email.lower():
        if user_repository.get_by_email(session, data.email) is not None:
            raise _email_taken()
        user.email = data.email
    try:
        with session.begin_nested():
            session.flush()
    except IntegrityError as exc:
        raise _email_taken() from exc
    session.commit()
    return user


def delete_account(session: Session, user: User, password: str) -> None:
    """Delete your own login (patients and doctors; an admin must not lock everyone out).

    Bookings stay, with the link cleared. A doctor's profile stays too, so the admin can
    give them a new login later.
    """
    if user.role == UserRole.ADMIN:
        raise ForbiddenError("Administrator accounts cannot be deleted here")
    if not verify_password(password, user.password_hash):
        raise ValidationFailed("password", "is incorrect")
    user_repository.delete(session, user)
    session.commit()


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
