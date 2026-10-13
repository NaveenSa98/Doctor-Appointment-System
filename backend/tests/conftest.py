"""Shared fixtures. Tests are hermetic: no real database or .env file is needed."""

from collections.abc import Callable, Iterator
from typing import Any

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

from app.core.config import Settings
from app.main import create_app

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
