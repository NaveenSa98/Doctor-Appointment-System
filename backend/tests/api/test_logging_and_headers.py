import logging

import pytest
from fastapi.testclient import TestClient


def test_request_log_contains_no_query_string_or_body(
    client: TestClient, caplog: pytest.LogCaptureFixture
) -> None:
    with caplog.at_level(logging.DEBUG):
        client.post("/health?q=jane-doe", json={"patient_name": "Jane Doe"})
    # Only inspect our own loggers: the test client's httpx logger records the URL.
    app_log = "\n".join(r.getMessage() for r in caplog.records if r.name.startswith("app"))
    assert app_log
    assert "jane-doe" not in app_log
    assert "Jane Doe" not in app_log
    assert "q=" not in app_log


def test_request_log_records_method_status_and_duration(
    client: TestClient, caplog: pytest.LogCaptureFixture
) -> None:
    with caplog.at_level(logging.INFO, logger="app.request"):
        client.get("/nope")
    message = "\n".join(r.getMessage() for r in caplog.records if r.name == "app.request")
    assert "GET" in message
    assert "404" in message
    assert "ms" in message


def test_response_has_request_id_and_security_headers(client: TestClient) -> None:
    response = client.get("/nope")
    assert response.headers["x-request-id"]
    assert response.headers["x-content-type-options"] == "nosniff"
    assert response.headers["referrer-policy"] == "no-referrer"


def test_cors_allows_configured_origin_only(client: TestClient) -> None:
    allowed = client.get("/nope", headers={"Origin": "http://localhost:5173"})
    assert allowed.headers.get("access-control-allow-origin") == "http://localhost:5173"
    denied = client.get("/nope", headers={"Origin": "http://evil.test"})
    assert "access-control-allow-origin" not in denied.headers
