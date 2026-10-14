"""Database access for users."""

import uuid
from collections.abc import Sequence

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.models import User


def get_by_email(session: Session, email: str) -> User | None:
    """Find a user by email, ignoring case and surrounding spaces."""
    return session.scalar(select(User).where(func.lower(User.email) == email.strip().lower()))


def get_by_id(session: Session, user_id: uuid.UUID) -> User | None:
    """Find a user by id."""
    return session.get(User, user_id)


def add(session: Session, user: User) -> None:
    """Insert a user."""
    session.add(user)
    session.flush()


def delete(session: Session, user: User) -> None:
    """Remove a user. Appointments they created are kept, with the link cleared."""
    session.delete(user)
    session.flush()


def get_by_doctor_id(session: Session, doctor_id: uuid.UUID) -> User | None:
    """The login linked to a doctor profile, if one exists."""
    return session.scalar(select(User).where(User.doctor_id == doctor_id))


def by_doctor_ids(session: Session, doctor_ids: Sequence[uuid.UUID]) -> dict[uuid.UUID, User]:
    """Logins keyed by the doctor profile they belong to."""
    users = session.scalars(select(User).where(User.doctor_id.in_(doctor_ids)))
    return {user.doctor_id: user for user in users if user.doctor_id is not None}
