from collections.abc import Iterator

from fastapi import FastAPI
from fastapi.testclient import TestClient
from sqlalchemy.exc import OperationalError

from app.db.session import get_session


class _OkSession:
    def execute(self, *_args: object, **_kwargs: object) -> None:
        return None


class _BrokenSession:
    def execute(self, *_args: object, **_kwargs: object) -> None:
        raise OperationalError("SELECT 1", {}, Exception("connection refused"))


def test_health_ok(app: FastAPI, client: TestClient) -> None:
    def _ok() -> Iterator[_OkSession]:
        yield _OkSession()

    app.dependency_overrides[get_session] = _ok
    response = client.get("/health")
    assert response.status_code == 200
    assert response.json() == {"status": "ok"}


def test_health_returns_503_when_database_is_down(app: FastAPI, client: TestClient) -> None:
    def _broken() -> Iterator[_BrokenSession]:
        yield _BrokenSession()

    app.dependency_overrides[get_session] = _broken
    response = client.get("/health")
    assert response.status_code == 503
    body = response.json()
    assert body["error"]["code"] == "service_unavailable"
    assert "connection refused" not in response.text
