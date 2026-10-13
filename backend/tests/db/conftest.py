"""Database fixtures. DB tests are skipped when no migrations URL is configured."""

from collections.abc import Iterator
from pathlib import Path

import pytest
from alembic.config import Config
from pydantic import ValidationError
from sqlalchemy import Engine
from sqlalchemy.orm import Session

from alembic import command
from app.core.config import Settings
from tests.db.schema import assert_test_schema, temp_schema_engine

BACKEND_DIR = Path(__file__).resolve().parents[2]


@pytest.fixture(scope="session")
def migrations_url() -> str:
    """The session-pooler URL used for migrations and tests (from backend/.env)."""
    try:
        url = Settings().database_url_migrations
    except ValidationError:
        pytest.skip("backend/.env is not configured")
    if not url:
        pytest.skip("DATABASE_URL_MIGRATIONS is not set")
    return url


def run_alembic(engine: Engine, action: str, revision: str) -> None:
    """Run an Alembic command on a connection from the given (schema-pinned) engine."""
    config = Config(str(BACKEND_DIR / "alembic.ini"))
    config.set_main_option("script_location", str(BACKEND_DIR / "alembic"))
    with engine.begin() as connection:
        assert_test_schema(connection)
        config.attributes["connection"] = connection
        getattr(command, action)(config, revision)


@pytest.fixture
def fresh_engine(migrations_url: str) -> Iterator[Engine]:
    """An engine on an empty throwaway schema (no migrations applied)."""
    with temp_schema_engine(migrations_url) as engine:
        yield engine


@pytest.fixture(scope="session")
def migrated_engine(migrations_url: str) -> Iterator[Engine]:
    """An engine on a throwaway schema with all migrations applied, shared by the session."""
    with temp_schema_engine(migrations_url) as engine:
        run_alembic(engine, "upgrade", "head")
        yield engine


@pytest.fixture
def db_session(migrated_engine: Engine) -> Iterator[Session]:
    """A session whose work is rolled back after each test."""
    connection = migrated_engine.connect()
    transaction = connection.begin()
    assert_test_schema(connection)
    session = Session(bind=connection, join_transaction_mode="create_savepoint")
    try:
        yield session
    finally:
        session.close()
        transaction.rollback()
        connection.close()
