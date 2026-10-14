"""Staff view of registered patients: list, search, detail, and who may see whom."""

from dataclasses import dataclass

import pytest
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from app.models import Appointment, Doctor, User, UserRole
from tests.api.helpers import auth_header, future_slot, iso
from tests.db.factories import make_appointment, make_doctor, make_hospital, make_user

URL = "/api/v1/patients"


@dataclass
class World:
    admin: User
    doctor1: Doctor
    doctor2: Doctor
    doctor1_user: User
    alice: User
    bob: User
    carol: User
    alice_first: Appointment
    alice_last: Appointment


def patient(session: Session, name: str, email: str) -> User:
    user = make_user(session, role=UserRole.PATIENT, email=email)
    user.full_name = name
    session.flush()
    return user


@pytest.fixture
def world(db_session: Session) -> World:
    hospital = make_hospital(db_session)
    doctor1 = make_doctor(db_session, [hospital])
    doctor2 = make_doctor(db_session, [hospital])
    alice = patient(db_session, "Alice Perera", "alice@example.test")
    bob = patient(db_session, "Bob Silva", "bob@example.test")
    carol = patient(db_session, "Carol Jay", "carol@example.test")  # never booked

    def book(doctor: Doctor, who: User | None, day: int, **fields: object) -> Appointment:
        return make_appointment(
            db_session,
            doctor,
            hospital,
            future_slot(day, 9, 0),
            created_by=who.id if who else None,
            **fields,
        )

    alice_first = book(doctor1, alice, 2)
    book(doctor2, alice, 3)
    alice_last = book(doctor1, alice, 4)
    book(doctor1, alice, 5, deleted_at=future_slot(1))  # soft-deleted: never counted
    book(doctor2, bob, 6)
    book(doctor1, None, 7)  # a guest booking belongs to no account
    return World(
        admin=make_user(db_session),
        doctor1=doctor1,
        doctor2=doctor2,
        doctor1_user=make_user(db_session, role=UserRole.DOCTOR, doctor=doctor1),
        alice=alice,
        bob=bob,
        carol=carol,
        alice_first=alice_first,
        alice_last=alice_last,
    )


def names(response: object) -> list[str]:
    return [item["full_name"] for item in response.json()["items"]]  # type: ignore[attr-defined]


def test_only_staff_may_look(db_client: TestClient, world: World, db_session: Session) -> None:
    assert db_client.get(URL).status_code == 401
    patient_headers = auth_header(world.alice)
    assert db_client.get(URL, headers=patient_headers).status_code == 403
    assert db_client.get(f"{URL}/{world.bob.id}", headers=patient_headers).status_code == 403


def test_admin_sees_every_patient_with_booking_counts(db_client: TestClient, world: World) -> None:
    response = db_client.get(URL, headers=auth_header(world.admin))
    assert response.status_code == 200
    body = response.json()
    assert names(response) == ["Alice Perera", "Bob Silva", "Carol Jay"]
    assert body["total"] == 3  # staff accounts are not patients
    alice, bob, carol = body["items"]
    assert alice["booking_count"] == 3  # the deleted booking is not counted
    assert alice["last_booking_at"] == iso(world.alice_last.start_time)
    assert alice["email"] == "alice@example.test"
    assert (bob["booking_count"], carol["booking_count"]) == (1, 0)
    assert carol["last_booking_at"] is None
    assert "password" not in response.text


def test_search_by_name_or_email_ignoring_case(db_client: TestClient, world: World) -> None:
    headers = auth_header(world.admin)
    assert names(db_client.get(URL, params={"q": "ALICE"}, headers=headers)) == ["Alice Perera"]
    assert names(db_client.get(URL, params={"q": "silva"}, headers=headers)) == ["Bob Silva"]
    assert names(db_client.get(URL, params={"q": "carol@exam"}, headers=headers)) == ["Carol Jay"]
    assert names(db_client.get(URL, params={"q": "  "}, headers=headers)) != []  # blank = no search


def test_search_treats_wildcards_literally(db_client: TestClient, world: World) -> None:
    for q in ("%", "_", "\\"):
        response = db_client.get(URL, params={"q": q}, headers=auth_header(world.admin))
        assert response.json()["total"] == 0


def test_pagination(db_client: TestClient, world: World) -> None:
    headers = auth_header(world.admin)
    first = db_client.get(URL, params={"page_size": 2}, headers=headers).json()
    assert (first["total"], first["pages"], len(first["items"])) == (3, 2, 2)
    second = db_client.get(URL, params={"page_size": 2, "page": 2}, headers=headers).json()
    assert [item["full_name"] for item in second["items"]] == ["Carol Jay"]


@pytest.mark.parametrize("params", [{"page_size": 101}, {"page": 0}, {"sort": "name"}])
def test_bad_queries_are_422(
    db_client: TestClient, world: World, params: dict[str, object]
) -> None:
    response = db_client.get(URL, params=params, headers=auth_header(world.admin))
    assert response.status_code == 422


def test_a_doctor_only_sees_patients_who_booked_with_them(
    db_client: TestClient, world: World
) -> None:
    headers = auth_header(world.doctor1_user)
    response = db_client.get(URL, headers=headers)
    assert names(response) == ["Alice Perera"]  # not Bob (doctor2 only), not Carol
    alice = response.json()["items"][0]
    assert alice["booking_count"] == 2  # only her bookings with this doctor
    assert alice["last_booking_at"] == iso(world.alice_last.start_time)
    assert db_client.get(URL, params={"q": "bob"}, headers=headers).json()["total"] == 0


def test_admin_detail_lists_all_bookings_latest_first(db_client: TestClient, world: World) -> None:
    response = db_client.get(f"{URL}/{world.alice.id}", headers=auth_header(world.admin))
    assert response.status_code == 200
    body = response.json()
    assert body["full_name"] == "Alice Perera"
    assert body["booking_count"] == 3
    ids = [booking["id"] for booking in body["bookings"]]
    assert len(ids) == 3  # the soft-deleted booking is not shown
    assert ids[0] == str(world.alice_last.id)
    assert ids[-1] != ids[0]
    assert body["bookings"][0]["doctor"]["full_name"] == world.doctor1.full_name


def test_a_doctor_sees_only_their_own_bookings_of_a_patient(
    db_client: TestClient, world: World
) -> None:
    headers = auth_header(world.doctor1_user)
    body = db_client.get(f"{URL}/{world.alice.id}", headers=headers).json()
    assert {b["doctor"]["id"] for b in body["bookings"]} == {str(world.doctor1.id)}
    assert [b["id"] for b in body["bookings"]] == [
        str(world.alice_last.id),
        str(world.alice_first.id),
    ]

    # Bob never booked with doctor 1: indistinguishable from a patient who does not exist.
    assert db_client.get(f"{URL}/{world.bob.id}", headers=headers).status_code == 404


def test_unknown_ids_and_non_patients_are_404(db_client: TestClient, world: World) -> None:
    headers = auth_header(world.admin)
    missing = db_client.get(f"{URL}/00000000-0000-0000-0000-000000000000", headers=headers)
    assert missing.status_code == 404
    assert db_client.get(f"{URL}/{world.doctor1_user.id}", headers=headers).status_code == 404
    assert db_client.get(f"{URL}/{world.admin.id}", headers=headers).status_code == 404


def test_a_patient_with_no_bookings_still_has_a_page(db_client: TestClient, world: World) -> None:
    response = db_client.get(f"{URL}/{world.carol.id}", headers=auth_header(world.admin))
    assert response.status_code == 200
    assert response.json()["bookings"] == []
    assert response.json()["booking_count"] == 0
