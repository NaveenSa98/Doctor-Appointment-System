"""Database engine and per-request session dependency."""

from collections.abc import Iterator

from fastapi import Request
from sqlalchemy import Engine, create_engine
from sqlalchemy.orm import Session

from app.core.config import Settings


def make_engine(settings: Settings) -> Engine:
    """Create the engine. It connects lazily, so startup does not need the database.

    The pool is small because Supabase's pooler multiplexes connections, and prepared
    statements are disabled because the pooler runs in transaction mode.
    """
    return create_engine(
        settings.database_url,
        pool_size=5,
        max_overflow=5,
        pool_pre_ping=True,
        connect_args={"prepare_threshold": None, "connect_timeout": 5},
    )


def get_session(request: Request) -> Iterator[Session]:
    """Yield a session bound to the app's engine and close it afterwards."""
    with Session(request.app.state.engine) as session:
        yield session
