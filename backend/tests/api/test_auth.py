"""Auth endpoints and dependencies. These run against the test schema on Supabase."""

import logging
import uuid
from datetime import timedelta
from typing import Annotated

import jwt
import pytest
from fastapi import Depends, FastAPI
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from app.api.v1.deps import get_now, get_optional_user, require_role
from app.core.clock import utcnow
from app.core.security import create_access_token
from app.main import create_app
from app.models import User, UserRole
from tests.conftest import VALID_SECRET, client_with_session, make_settings
from tests.db.factories import make_doctor, make_hospital, make_user

PASSWORD = "correct-horse-battery"


def _token_for(user: User, secret: str = VALID_SECRET) -> str:
    return create_access_token(user.id, user.role.value, secret, utcnow(), timedelta(minutes=30))


def _bearer(token: str) -> dict[str, str]:
    return {"Authorization": f"Bearer {token}"}


@pytest.fixture
def admin(db_session: Session) -> User:
    return make_user(db_session, email="Admin@Demo.test", password=PASSWORD)


def test_login_returns_a_token_and_the_user(db_client: TestClient, admin: User) -> None:
    response = db_client.post(
        "/api/v1/auth/login", json={"email": "admin@demo.test", "password": PASSWORD}
    )
    assert response.status_code == 200
    body = response.json()
    assert body["token_type"] == "bearer"
    assert body["expires_in"] == 30 * 60
    assert body["user"] == {
        "id": str(admin.id),
        "email": "Admin@Demo.test",
        "role": "admin",
        "doctor_id": None,
    }
    assert "password" not in response.text


def test_token_carries_only_the_expected_claims(db_client: TestClient, admin: User) -> None:
    body = db_client.post(
        "/api/v1/auth/login", json={"email": "admin@demo.test", "password": PASSWORD}
    ).json()
    claims = jwt.decode(body["access_token"], options={"verify_signature": False})
    assert set(claims) == {"sub", "role", "iat", "exp"}


def test_wrong_password_and_unknown_email_look_identical(
    db_client: TestClient, admin: User
) -> None:
    wrong = db_client.post(
        "/api/v1/auth/login", json={"email": "admin@demo.test", "password": "nope"}
    )
    unknown = db_client.post(
        "/api/v1/auth/login", json={"email": "nobody@demo.test", "password": PASSWORD}
    )
    assert wrong.status_code == unknown.status_code == 401
    assert wrong.json() == unknown.json()
    assert wrong.json()["error"]["code"] == "invalid_credentials"


def test_inactive_user_cannot_log_in(db_client: TestClient, db_session: Session) -> None:
    user = make_user(db_session, email="off@demo.test", password=PASSWORD)
    user.is_active = False
    db_session.flush()
    response = db_client.post(
        "/api/v1/auth/login", json={"email": "off@demo.test", "password": PASSWORD}
    )
    assert response.status_code == 401
    assert response.json()["error"]["code"] == "invalid_credentials"


def test_login_validates_its_input(db_client: TestClient) -> None:
    missing = db_client.post("/api/v1/auth/login", json={"email": "a@demo.test"})
    assert missing.status_code == 422
    assert missing.json()["error"]["details"][0]["field"] == "password"
    extra = db_client.post(
        "/api/v1/auth/login", json={"email": "a@demo.test", "password": "x", "admin": True}
    )
    assert extra.status_code == 422


def test_me_returns_the_signed_in_user(db_client: TestClient, admin: User) -> None:
    response = db_client.get("/api/v1/auth/me", headers=_bearer(_token_for(admin)))
    assert response.status_code == 200
    assert response.json()["id"] == str(admin.id)


def test_me_without_a_token_is_unauthorized(db_client: TestClient) -> None:
    response = db_client.get("/api/v1/auth/me")
    assert response.status_code == 401
    assert response.json()["error"]["code"] == "unauthorized"
    assert response.headers["www-authenticate"] == "Bearer"


@pytest.mark.parametrize("header", ["Basic abc", "Bearer", "Bearer ", "token"])
def test_malformed_authorization_header_is_unauthorized(db_client: TestClient, header: str) -> None:
    response = db_client.get("/api/v1/auth/me", headers={"Authorization": header})
    assert response.status_code == 401


def test_tampered_or_foreign_tokens_are_unauthorized(db_client: TestClient, admin: User) -> None:
    foreign = _token_for(admin, secret="o" * 40)
    assert db_client.get("/api/v1/auth/me", headers=_bearer(foreign)).status_code == 401
    tampered = _token_for(admin)[:-3] + "abc"
    assert db_client.get("/api/v1/auth/me", headers=_bearer(tampered)).status_code == 401


def test_expired_token_is_unauthorized(app: FastAPI, db_session: Session, admin: User) -> None:
    app.dependency_overrides[get_now] = lambda: utcnow() + timedelta(minutes=31)
    with client_with_session(app, db_session) as client:
        response = client.get("/api/v1/auth/me", headers=_bearer(_token_for(admin)))
    assert response.status_code == 401


def test_token_of_a_disabled_or_missing_user_is_unauthorized(
    db_client: TestClient, db_session: Session, admin: User
) -> None:
    token = _token_for(admin)
    admin.is_active = False
    db_session.flush()
    assert db_client.get("/api/v1/auth/me", headers=_bearer(token)).status_code == 401

    ghost = create_access_token(
        uuid.uuid4(), "admin", VALID_SECRET, utcnow(), timedelta(minutes=30)
    )
    assert db_client.get("/api/v1/auth/me", headers=_bearer(ghost)).status_code == 401


def test_optional_user_is_none_for_anonymous_but_401_for_a_bad_token(
    app: FastAPI, db_session: Session, admin: User
) -> None:
    @app.get("/_test/optional")
    def optional(user: Annotated[User | None, Depends(get_optional_user)]) -> dict[str, str | None]:
        return {"email": user.email if user else None}

    with client_with_session(app, db_session) as client:
        assert client.get("/_test/optional").json() == {"email": None}
        signed_in = client.get("/_test/optional", headers=_bearer(_token_for(admin)))
        assert signed_in.json() == {"email": "Admin@Demo.test"}
        assert client.get("/_test/optional", headers=_bearer("garbage")).status_code == 401


def test_require_role_allows_only_the_listed_roles(
    app: FastAPI, db_session: Session, admin: User
) -> None:
    @app.get("/_test/admin-only")
    def admin_only(user: Annotated[User, Depends(require_role(UserRole.ADMIN))]) -> dict[str, str]:
        return {"role": user.role.value}

    hospital = make_hospital(db_session)
    doctor = make_doctor(db_session, [hospital])
    doctor_user = make_user(db_session, role=UserRole.DOCTOR, doctor=doctor)

    with client_with_session(app, db_session) as client:
        assert client.get("/_test/admin-only").status_code == 401
        forbidden = client.get("/_test/admin-only", headers=_bearer(_token_for(doctor_user)))
        assert forbidden.status_code == 403
        assert forbidden.json()["error"]["code"] == "forbidden"
        allowed = client.get("/_test/admin-only", headers=_bearer(_token_for(admin)))
        assert allowed.status_code == 200


def test_login_is_rate_limited_per_client(db_session: Session) -> None:
    app = create_app(make_settings(login_rate_limit_per_minute=3))
    with client_with_session(app, db_session) as client:
        attempt = {"email": "nobody@demo.test", "password": "wrong"}
        codes = [client.post("/api/v1/auth/login", json=attempt).status_code for _ in range(4)]
        blocked = client.post("/api/v1/auth/login", json=attempt)
    assert codes == [401, 401, 401, 429]
    assert blocked.json()["error"]["code"] == "rate_limited"
    assert int(blocked.headers["retry-after"]) >= 1


def test_logs_never_contain_credentials_or_tokens(
    db_client: TestClient, admin: User, caplog: pytest.LogCaptureFixture
) -> None:
    with caplog.at_level(logging.DEBUG):
        body = db_client.post(
            "/api/v1/auth/login", json={"email": "admin@demo.test", "password": PASSWORD}
        ).json()
        db_client.get("/api/v1/auth/me", headers=_bearer(body["access_token"]))
    app_log = "\n".join(r.getMessage() for r in caplog.records if r.name.startswith("app"))
    assert app_log
    for secret in (PASSWORD, body["access_token"], "admin@demo.test"):
        assert secret not in app_log
