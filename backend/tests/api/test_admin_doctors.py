"""Admin management of doctors: create, edit, deactivate, delete, and their logins."""

import uuid
from dataclasses import dataclass
from typing import Any

import pytest
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from app.models import Doctor, Hospital, User, UserRole
from tests.api.helpers import auth_header, future_slot
from tests.db.factories import make_appointment, make_doctor, make_hospital, make_user

URL = "/api/v1/admin/doctors"
PASSWORD = "initial-password-1"


@dataclass
class World:
    admin: User
    hospital_a: Hospital
    hospital_b: Hospital

    @property
    def headers(self) -> dict[str, str]:
        return auth_header(self.admin)


@pytest.fixture
def world(db_session: Session) -> World:
    return World(
        admin=make_user(db_session),
        hospital_a=make_hospital(db_session, "Alpha Hospital"),
        hospital_b=make_hospital(db_session, "Beta Clinic"),
    )


def new_doctor(world: World, **overrides: Any) -> dict[str, Any]:
    body: dict[str, Any] = {
        "full_name": "Dr. Nadia Perera",
        "specialty": "Cardiology",
        "hospital_ids": [str(world.hospital_a.id)],
        "account": {"email": "nadia@clinic.test", "password": PASSWORD},
    }
    body.update(overrides)
    return body


def create(client: TestClient, world: World, **overrides: Any) -> Any:
    return client.post(URL, json=new_doctor(world, **overrides), headers=world.headers)


# ---- who may use it ---------------------------------------------------------------------------


def test_the_endpoints_need_an_admin(db_client: TestClient, db_session: Session) -> None:
    hospital = make_hospital(db_session)
    doctor = make_doctor(db_session, [hospital])
    for headers, expected in (
        ({}, 401),
        (auth_header(make_user(db_session, role=UserRole.DOCTOR, doctor=doctor)), 403),
        (auth_header(make_user(db_session, role=UserRole.PATIENT)), 403),
    ):
        assert db_client.get(URL, headers=headers).status_code == expected
        assert db_client.post(URL, json={}, headers=headers).status_code == expected
        assert db_client.delete(f"{URL}/{doctor.id}", headers=headers).status_code == expected


# ---- create -----------------------------------------------------------------------------------


def test_create_a_doctor_with_a_login_that_works(db_client: TestClient, world: World) -> None:
    response = create(
        db_client, world, hospital_ids=[str(world.hospital_a.id), str(world.hospital_b.id)]
    )
    assert response.status_code == 201
    body = response.json()
    assert response.headers["Location"] == f"/api/v1/admin/doctors/{body['id']}"
    assert body["full_name"] == "Dr. Nadia Perera"
    assert body["is_active"] is True
    assert body["appointment_count"] == 0
    assert [h["name"] for h in body["hospitals"]] == ["Alpha Hospital", "Beta Clinic"]
    assert body["account"]["email"] == "nadia@clinic.test"
    assert "password" not in response.text

    login = db_client.post(
        "/api/v1/auth/login", json={"email": "nadia@clinic.test", "password": PASSWORD}
    )
    assert login.status_code == 200
    assert login.json()["user"]["role"] == "doctor"
    assert login.json()["user"]["doctor_id"] == body["id"]


def test_create_without_a_login_and_add_it_later(db_client: TestClient, world: World) -> None:
    body = create(db_client, world, account=None).json()
    assert body["account"] is None

    later = db_client.put(
        f"{URL}/{body['id']}/account",
        json={"email": "later@clinic.test", "password": PASSWORD},
        headers=world.headers,
    )
    assert later.status_code == 200
    assert later.json()["account"]["email"] == "later@clinic.test"


def test_a_new_doctor_appears_in_the_public_list(db_client: TestClient, world: World) -> None:
    create(db_client, world)
    names = [d["full_name"] for d in db_client.get("/api/v1/doctors").json()]
    assert "Dr. Nadia Perera" in names


@pytest.mark.parametrize(
    "overrides",
    [
        {"hospital_ids": []},
        {"full_name": "x"},
        {"specialty": ""},
        {"account": {"email": "nope", "password": PASSWORD}},
        {"account": {"email": "a@clinic.test", "password": "short"}},
        {"role": "admin"},
    ],
)
def test_invalid_doctors_are_422(
    db_client: TestClient, world: World, overrides: dict[str, Any]
) -> None:
    assert create(db_client, world, **overrides).status_code == 422


def test_unknown_hospital_is_a_422_on_hospital_ids(db_client: TestClient, world: World) -> None:
    response = create(db_client, world, hospital_ids=["00000000-0000-0000-0000-000000000000"])
    assert response.status_code == 422
    assert response.json()["error"]["details"][0]["field"] == "hospital_ids"


def test_duplicate_login_email_is_a_409_and_creates_nothing(
    db_client: TestClient, world: World, db_session: Session
) -> None:
    make_user(db_session, email="taken@clinic.test")
    response = create(
        db_client, world, account={"email": "TAKEN@clinic.test", "password": PASSWORD}
    )
    assert response.status_code == 409
    assert response.json()["error"]["code"] == "email_taken"
    assert db_client.get(URL, headers=world.headers).json() == []


# ---- list and read ----------------------------------------------------------------------------


def test_list_includes_inactive_doctors_and_booking_counts(
    db_client: TestClient, world: World, db_session: Session
) -> None:
    busy = make_doctor(db_session, [world.hospital_a], name="Dr. Busy")
    make_appointment(db_session, busy, world.hospital_a, future_slot(3))
    make_appointment(db_session, busy, world.hospital_a, future_slot(4), deleted_at=future_slot(1))
    idle = make_doctor(db_session, [world.hospital_a], name="Dr. Idle")
    idle.is_active = False
    db_session.flush()

    rows = {row["full_name"]: row for row in db_client.get(URL, headers=world.headers).json()}
    assert rows["Dr. Busy"]["appointment_count"] == 1  # the deleted booking is not counted
    assert rows["Dr. Idle"]["is_active"] is False
    assert rows["Dr. Idle"]["account"] is None


def test_get_one_and_unknown_is_404(db_client: TestClient, world: World) -> None:
    created = create(db_client, world).json()
    assert (
        db_client.get(f"{URL}/{created['id']}", headers=world.headers).json()["id"] == created["id"]
    )
    missing = db_client.get(f"{URL}/00000000-0000-0000-0000-000000000000", headers=world.headers)
    assert missing.status_code == 404


# ---- edit -------------------------------------------------------------------------------------


def test_edit_name_specialty_and_hospitals(db_client: TestClient, world: World) -> None:
    created = create(db_client, world).json()
    response = db_client.patch(
        f"{URL}/{created['id']}",
        json={
            "full_name": "Dr. Nadia P. Perera",
            "specialty": "Neurology",
            "hospital_ids": [str(world.hospital_b.id)],
        },
        headers=world.headers,
    )
    assert response.status_code == 200
    body = response.json()
    assert (body["full_name"], body["specialty"]) == ("Dr. Nadia P. Perera", "Neurology")
    assert [h["name"] for h in body["hospitals"]] == ["Beta Clinic"]
    assert body["account"]["email"] == "nadia@clinic.test"


@pytest.mark.parametrize("body", [{}, {"full_name": None}, {"hospital_ids": []}, {"id": "x"}])
def test_invalid_edits_are_422(db_client: TestClient, world: World, body: dict[str, Any]) -> None:
    created = create(db_client, world).json()
    response = db_client.patch(f"{URL}/{created['id']}", json=body, headers=world.headers)
    assert response.status_code == 422


def test_a_hospital_with_bookings_cannot_be_removed(
    db_client: TestClient, world: World, db_session: Session
) -> None:
    doctor = make_doctor(db_session, [world.hospital_a, world.hospital_b])
    make_appointment(db_session, doctor, world.hospital_a, future_slot(3))

    blocked = db_client.patch(
        f"{URL}/{doctor.id}",
        json={"hospital_ids": [str(world.hospital_b.id)]},
        headers=world.headers,
    )
    assert blocked.status_code == 409
    assert blocked.json()["error"]["code"] == "hospital_in_use"

    allowed = db_client.patch(
        f"{URL}/{doctor.id}",
        json={"hospital_ids": [str(world.hospital_a.id)]},
        headers=world.headers,
    )
    assert allowed.status_code == 200  # removing the unused hospital is fine


def test_deactivating_hides_the_doctor_and_blocks_their_login(
    db_client: TestClient, world: World
) -> None:
    created = create(db_client, world).json()
    off = db_client.patch(
        f"{URL}/{created['id']}", json={"is_active": False}, headers=world.headers
    )
    assert off.status_code == 200
    assert off.json()["account"]["is_active"] is False

    public = [d["id"] for d in db_client.get("/api/v1/doctors").json()]
    assert created["id"] not in public
    login = db_client.post(
        "/api/v1/auth/login", json={"email": "nadia@clinic.test", "password": PASSWORD}
    )
    assert login.status_code == 401

    db_client.patch(f"{URL}/{created['id']}", json={"is_active": True}, headers=world.headers)
    again = db_client.post(
        "/api/v1/auth/login", json={"email": "nadia@clinic.test", "password": PASSWORD}
    )
    assert again.status_code == 200


# ---- the doctor's login -----------------------------------------------------------------------


def test_reset_the_password_and_change_the_email(db_client: TestClient, world: World) -> None:
    created = create(db_client, world).json()
    response = db_client.put(
        f"{URL}/{created['id']}/account",
        json={"email": "new@clinic.test", "password": "a-brand-new-password"},
        headers=world.headers,
    )
    assert response.status_code == 200
    login = db_client.post(
        "/api/v1/auth/login", json={"email": "new@clinic.test", "password": "a-brand-new-password"}
    )
    assert login.status_code == 200
    old = db_client.post(
        "/api/v1/auth/login", json={"email": "nadia@clinic.test", "password": PASSWORD}
    )
    assert old.status_code == 401


def test_creating_a_login_needs_both_email_and_password(
    db_client: TestClient, world: World
) -> None:
    created = create(db_client, world, account=None).json()
    only_email = db_client.put(
        f"{URL}/{created['id']}/account", json={"email": "a@clinic.test"}, headers=world.headers
    )
    assert only_email.status_code == 422
    empty = db_client.put(f"{URL}/{created['id']}/account", json={}, headers=world.headers)
    assert empty.status_code == 422


def test_a_login_email_cannot_be_reused(
    db_client: TestClient, world: World, db_session: Session
) -> None:
    make_user(db_session, email="taken@clinic.test")
    created = create(db_client, world).json()
    response = db_client.put(
        f"{URL}/{created['id']}/account", json={"email": "Taken@Clinic.test"}, headers=world.headers
    )
    assert response.status_code == 409


# ---- delete -----------------------------------------------------------------------------------


def test_delete_removes_the_doctor_and_their_login(
    db_client: TestClient, world: World, db_session: Session
) -> None:
    created = create(db_client, world).json()
    assert db_client.delete(f"{URL}/{created['id']}", headers=world.headers).status_code == 204

    assert db_client.get(f"{URL}/{created['id']}", headers=world.headers).status_code == 404
    login = db_client.post(
        "/api/v1/auth/login", json={"email": "nadia@clinic.test", "password": PASSWORD}
    )
    assert login.status_code == 401
    assert db_session.get(Doctor, uuid.UUID(created["id"])) is None


def test_a_doctor_with_appointments_cannot_be_deleted_but_can_be_deactivated(
    db_client: TestClient, world: World, db_session: Session
) -> None:
    doctor = make_doctor(db_session, [world.hospital_a])
    make_appointment(
        db_session, doctor, world.hospital_a, future_slot(3), deleted_at=future_slot(1)
    )

    blocked = db_client.delete(f"{URL}/{doctor.id}", headers=world.headers)
    assert blocked.status_code == 409
    assert blocked.json()["error"]["code"] == "doctor_has_appointments"

    off = db_client.patch(f"{URL}/{doctor.id}", json={"is_active": False}, headers=world.headers)
    assert off.status_code == 200


def test_delete_unknown_is_404(db_client: TestClient, world: World) -> None:
    missing = db_client.delete(f"{URL}/00000000-0000-0000-0000-000000000000", headers=world.headers)
    assert missing.status_code == 404
