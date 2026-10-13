from fastapi import FastAPI
from fastapi.testclient import TestClient
from pydantic import BaseModel


class _Payload(BaseModel):
    name: str


def test_unknown_route_uses_standard_error_shape(client: TestClient) -> None:
    response = client.get("/does-not-exist")
    assert response.status_code == 404
    error = response.json()["error"]
    assert error["code"] == "not_found"
    assert isinstance(error["message"], str)


def test_validation_failure_returns_422_with_field_details(app: FastAPI) -> None:
    @app.post("/_test/validate")
    def validate(payload: _Payload) -> dict[str, str]:
        return {"name": payload.name}

    with TestClient(app, raise_server_exceptions=False) as client:
        response = client.post("/_test/validate", json={})
    assert response.status_code == 422
    error = response.json()["error"]
    assert error["code"] == "validation_error"
    assert error["details"][0]["field"] == "name"
    assert error["details"][0]["message"]


def test_unhandled_exception_returns_500_without_stack_trace(app: FastAPI) -> None:
    @app.get("/_test/boom")
    def boom() -> None:
        raise RuntimeError("secret internal detail")

    with TestClient(app, raise_server_exceptions=False) as client:
        response = client.get("/_test/boom")
    assert response.status_code == 500
    assert response.json()["error"]["code"] == "internal_error"
    assert "secret internal detail" not in response.text
    assert "Traceback" not in response.text


def test_method_not_allowed_uses_standard_error_shape(client: TestClient) -> None:
    response = client.post("/health")
    assert response.status_code == 405
    assert response.json()["error"]["code"] == "method_not_allowed"
