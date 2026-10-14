"""Database access for users."""

import uuid

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
