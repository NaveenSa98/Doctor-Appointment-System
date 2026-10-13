"""Shared fixtures.

App-only tests are hermetic (no database or .env needed). Tests that use the database
fixtures run against a throwaway schema on Supabase and are skipped when
DATABASE_URL_MIGRATIONS is not configured.
"""

from collections.abc import Callable, Iterator
from typing import Any

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient
from pydantic import ValidationError
from sqlalchemy import Engine
from sqlalchemy.orm import Session

from app.core.config import Settings
from app.db.session import get_session
from app.main import create_app
from tests.db.schema import assert_test_schema, temp_schema_engine
from tests.db.support import run_alembic

VALID_SECRET = "x" * 40


def make_settings(**overrides: Any) -> Settings:
    """Build Settings from explicit values, ignoring any local .env file."""
    values: dict[str, Any] = {
        "database_url": "postgresql+psycopg://user:pass@localhost:5432/test",
        "jwt_secret": VALID_SECRET,
        "cors_origins": "http://localhost:5173",
    }
    values.update(overrides)
    return Settings(_env_file=None, **values)


@pytest.fixture
def settings() -> Settings:
    return make_settings()


@pytest.fixture
def app(settings: Settings) -> FastAPI:
    return create_app(settings)


@pytest.fixture
def client(app: FastAPI) -> Iterator[TestClient]:
    with TestClient(app, raise_server_exceptions=False) as test_client:
        yield test_client


@pytest.fixture
def make_client() -> Callable[[Settings], TestClient]:
    def _make(settings: Settings) -> TestClient:
        return TestClient(create_app(settings), raise_server_exceptions=False)

    return _make


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


def client_with_session(app: FastAPI, session: Session) -> TestClient:
    """A test client whose requests use the given (rolled-back-afterwards) session."""
    app.dependency_overrides[get_session] = lambda: session
    return TestClient(app, raise_server_exceptions=False)


@pytest.fixture
def db_client(app: FastAPI, db_session: Session) -> Iterator[TestClient]:
    """A client for the default app, backed by the test schema."""
    with client_with_session(app, db_session) as test_client:
        yield test_client
