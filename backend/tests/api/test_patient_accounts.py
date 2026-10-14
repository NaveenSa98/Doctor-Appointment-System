"""Patient sign-up, account settings, account deletion and what a patient may see."""

from dataclasses import dataclass
from typing import Any

import pytest
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from app.models import Doctor, Hospital, UserRole
from tests.api.helpers import auth_header, booking, future_slot
from tests.db.factories import make_appointment, make_doctor, make_hospital, make_user

AUTH = "/api/v1/auth"
APPOINTMENTS = "/api/v1/appointments"
PASSWORD = "correct-horse-battery"


@dataclass
class World:
    hospital: Hospital
    doctor: Doctor


@pytest.fixture
def world(db_session: Session) -> World:
    hospital = make_hospital(db_session)
    return World(hospital=hospital, doctor=make_doctor(db_session, [hospital]))


def register(
    client: TestClient, email: str = "pat@example.com", name: str = "Pat Patient", **extra: Any
) -> Any:
    body = {"full_name": name, "email": email, "password": PASSWORD, **extra}
    return client.post(f"{AUTH}/register", json=body)


def signed_in(client: TestClient, email: str = "pat@example.com") -> dict[str, str]:
    """Register a patient and return their Authorization header."""
    response = register(client, email)
    assert response.status_code == 201
    return {"Authorization": f"Bearer {response.json()['access_token']}"}


def book(client: TestClient, world: World, headers: dict[str, str], days: int, **extra: Any) -> Any:
    body = booking(world.doctor, world.hospital, future_slot(days, 9, 0), **extra)
    return client.post(APPOINTMENTS, json=body, headers=headers)


# ---- sign-up ------------------------------------------------------------------------------


def test_register_creates_a_patient_and_signs_them_in(db_client: TestClient) -> None:
    response = register(db_client)
    assert response.status_code == 201
    body = response.json()
    assert body["token_type"] == "bearer"
    assert body["user"]["role"] == "patient"
    assert body["user"]["full_name"] == "Pat Patient"
    assert body["user"]["doctor_id"] is None
    assert "password" not in str(body)

    me = db_client.get(f"{AUTH}/me", headers={"Authorization": f"Bearer {body['access_token']}"})
    assert me.status_code == 200
    assert me.json()["email"] == "pat@example.com"


def test_a_new_patient_can_sign_in_later(db_client: TestClient) -> None:
    register(db_client)
    login = db_client.post(f"{AUTH}/login", json={"email": "PAT@example.com", "password": PASSWORD})
    assert login.status_code == 200


def test_duplicate_email_is_a_409_ignoring_case(db_client: TestClient) -> None:
    assert register(db_client).status_code == 201
    response = register(db_client, email="Pat@Example.com")
    assert response.status_code == 409
    assert response.json()["error"]["code"] == "email_taken"


@pytest.mark.parametrize(
    "overrides",
    [
        {"password": "short"},
        {"email": "not-an-email"},
        {"full_name": "x"},
        {"role": "admin"},  # a role can never be chosen at sign-up
        {"doctor_id": "00000000-0000-0000-0000-000000000000"},
    ],
)
def test_invalid_sign_ups_are_422(db_client: TestClient, overrides: dict[str, Any]) -> None:
    response = db_client.post(
        f"{AUTH}/register",
        json={"full_name": "Pat Patient", "email": "pat@example.com", "password": PASSWORD}
        | overrides,
    )
    assert response.status_code == 422
    assert response.json()["error"]["code"] == "validation_error"


# ---- what a patient can see and do ----------------------------------------------------------


def test_a_patient_only_sees_their_own_bookings(
    db_client: TestClient, db_session: Session, world: World
) -> None:
    mine_headers = signed_in(db_client, "mine@example.com")
    other_headers = signed_in(db_client, "other@example.com")
    mine = book(db_client, world, mine_headers, 3)
    theirs = book(db_client, world, other_headers, 4)
    make_appointment(db_session, world.doctor, world.hospital, future_slot(5, 9, 0))  # staff-made
    assert mine.status_code == theirs.status_code == 201

    listing = db_client.get(APPOINTMENTS, headers=mine_headers).json()
    assert [item["id"] for item in listing["items"]] == [mine.json()["id"]]
    assert listing["total"] == 1

    assert (
        db_client.get(f"{APPOINTMENTS}/{mine.json()['id']}", headers=mine_headers).status_code
        == 200
    )
    hidden = db_client.get(f"{APPOINTMENTS}/{theirs.json()['id']}", headers=mine_headers)
    assert hidden.status_code == 404


def test_a_patient_cannot_choose_a_status(db_client: TestClient, world: World) -> None:
    headers = signed_in(db_client)
    assert book(db_client, world, headers, 3, status="confirmed").status_code == 422
    assert book(db_client, world, headers, 3, status="scheduled").status_code == 201


def test_a_patient_cannot_change_cancel_or_count_bookings(
    db_client: TestClient, world: World
) -> None:
    headers = signed_in(db_client)
    url = f"{APPOINTMENTS}/{book(db_client, world, headers, 3).json()['id']}"

    assert db_client.patch(url, json={"status": "cancelled"}, headers=headers).status_code == 403
    assert db_client.delete(url, headers=headers).status_code == 403
    assert db_client.get(f"{APPOINTMENTS}/stats", headers=headers).status_code == 403


def test_a_booking_made_while_signed_out_is_not_attached_to_anyone(
    db_client: TestClient, world: World
) -> None:
    headers = signed_in(db_client)
    guest = db_client.post(APPOINTMENTS, json=booking(world.doctor, world.hospital, future_slot(3)))
    assert guest.status_code == 201
    assert db_client.get(APPOINTMENTS, headers=headers).json()["total"] == 0


# ---- account settings ------------------------------------------------------------------------


def test_changing_the_name_needs_no_password(db_client: TestClient) -> None:
    headers = signed_in(db_client)
    response = db_client.patch(f"{AUTH}/me", json={"full_name": "  Patricia P  "}, headers=headers)
    assert response.status_code == 200
    assert response.json()["full_name"] == "Patricia P"


def test_changing_email_or_password_needs_the_current_password(db_client: TestClient) -> None:
    headers = signed_in(db_client)
    for body in (
        {"email": "new@example.com"},
        {"new_password": "another-long-password"},
        {"email": "new@example.com", "current_password": "wrong-password"},
    ):
        response = db_client.patch(f"{AUTH}/me", json=body, headers=headers)
        assert response.status_code == 422
        fields = [d["field"] for d in response.json()["error"]["details"]]
        assert fields == ["current_password"]


def test_changing_the_password_replaces_the_old_one(db_client: TestClient) -> None:
    headers = signed_in(db_client)
    response = db_client.patch(
        f"{AUTH}/me",
        json={"new_password": "another-long-password", "current_password": PASSWORD},
        headers=headers,
    )
    assert response.status_code == 200
    old = db_client.post(f"{AUTH}/login", json={"email": "pat@example.com", "password": PASSWORD})
    new = db_client.post(
        f"{AUTH}/login", json={"email": "pat@example.com", "password": "another-long-password"}
    )
    assert (old.status_code, new.status_code) == (401, 200)


def test_changing_the_email_works_and_cannot_take_an_existing_one(db_client: TestClient) -> None:
    register(db_client, email="taken@example.com", name="Someone Else")
    headers = signed_in(db_client)

    clash = db_client.patch(
        f"{AUTH}/me",
        json={"email": "TAKEN@example.com", "current_password": PASSWORD},
        headers=headers,
    )
    assert clash.status_code == 409

    ok = db_client.patch(
        f"{AUTH}/me",
        json={"email": "fresh@example.com", "current_password": PASSWORD},
        headers=headers,
    )
    assert ok.status_code == 200
    assert ok.json()["email"] == "fresh@example.com"


def test_an_empty_or_null_profile_update_is_422(db_client: TestClient) -> None:
    headers = signed_in(db_client)
    assert db_client.patch(f"{AUTH}/me", json={}, headers=headers).status_code == 422
    assert (
        db_client.patch(f"{AUTH}/me", json={"full_name": None}, headers=headers).status_code == 422
    )
    assert db_client.patch(f"{AUTH}/me", json={"role": "admin"}, headers=headers).status_code == 422


# ---- deleting the account --------------------------------------------------------------------


def delete_account(client: TestClient, headers: dict[str, str], password: str) -> Any:
    return client.request("DELETE", f"{AUTH}/me", json={"password": password}, headers=headers)


def test_deleting_needs_the_right_password(db_client: TestClient) -> None:
    headers = signed_in(db_client)
    response = delete_account(db_client, headers, "wrong-password")
    assert response.status_code == 422
    assert db_client.get(f"{AUTH}/me", headers=headers).status_code == 200


def test_deleting_removes_the_login_but_keeps_the_bookings(
    db_client: TestClient, db_session: Session, world: World
) -> None:
    headers = signed_in(db_client)
    booked = book(db_client, world, headers, 3)

    assert delete_account(db_client, headers, PASSWORD).status_code == 204

    assert db_client.get(f"{AUTH}/me", headers=headers).status_code == 401
    login = db_client.post(f"{AUTH}/login", json={"email": "pat@example.com", "password": PASSWORD})
    assert login.status_code == 401

    admin = auth_header(make_user(db_session))
    items = db_client.get(APPOINTMENTS, headers=admin).json()["items"]
    assert [(i["id"], i["patient_name"]) for i in items] == [
        (booked.json()["id"], booked.json()["patient_name"])
    ]


def test_the_email_can_be_used_again_after_deleting(db_client: TestClient) -> None:
    headers = signed_in(db_client)
    assert delete_account(db_client, headers, PASSWORD).status_code == 204
    assert register(db_client).status_code == 201


def test_an_admin_cannot_delete_their_own_account(
    db_client: TestClient, db_session: Session
) -> None:
    admin = make_user(db_session, password=PASSWORD)
    response = delete_account(db_client, auth_header(admin), PASSWORD)
    assert response.status_code == 403
    assert db_client.get(f"{AUTH}/me", headers=auth_header(admin)).status_code == 200


def test_a_doctor_can_delete_their_login_but_the_profile_stays(
    db_client: TestClient, db_session: Session, world: World
) -> None:
    doctor_user = make_user(
        db_session,
        role=UserRole.DOCTOR,
        doctor=world.doctor,
        email="doc@clinic.test",
        password=PASSWORD,
    )
    make_appointment(
        db_session, world.doctor, world.hospital, future_slot(3), created_by=doctor_user.id
    )

    wrong = delete_account(db_client, auth_header(doctor_user), "wrong-password")
    assert wrong.status_code == 422
    assert delete_account(db_client, auth_header(doctor_user), PASSWORD).status_code == 204

    login = db_client.post(f"{AUTH}/login", json={"email": "doc@clinic.test", "password": PASSWORD})
    assert login.status_code == 401

    admin = make_user(db_session)
    row = db_client.get(
        f"/api/v1/admin/doctors/{world.doctor.id}", headers=auth_header(admin)
    ).json()
    assert row["account"] is None
    assert row["is_active"] is True
    assert row["appointment_count"] == 1

    restored = db_client.put(
        f"/api/v1/admin/doctors/{world.doctor.id}/account",
        json={"email": "doc@clinic.test", "password": PASSWORD},
        headers=auth_header(admin),
    )
    assert restored.status_code == 200  # the admin can give them a new login
