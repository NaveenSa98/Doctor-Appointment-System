"""Alembic environment. Online mode only; the URL is DATABASE_URL_MIGRATIONS (session pooler)."""

from sqlalchemy import Connection, create_engine
from sqlalchemy.pool import NullPool

from alembic import context
from app.core.config import get_settings
from app.models import Base

config = context.config
target_metadata = Base.metadata


def _migrate(connection: Connection) -> None:
    context.configure(connection=connection, target_metadata=target_metadata, compare_type=True)
    with context.begin_transaction():
        context.run_migrations()


def run_migrations_online() -> None:
    """Use a connection supplied by the caller (tests), or open one from the settings."""
    supplied = config.attributes.get("connection")
    if supplied is not None:
        _migrate(supplied)
        return

    url = get_settings().database_url_migrations
    if not url:
        raise RuntimeError("DATABASE_URL_MIGRATIONS is not set")
    engine = create_engine(url, poolclass=NullPool)
    with engine.connect() as connection:
        _migrate(connection)


if context.is_offline_mode():
    raise RuntimeError("Offline migrations are not supported")
run_migrations_online()
