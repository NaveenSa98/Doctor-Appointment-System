"""Appointment create, read, update and delete. Runs against the test schema on Supabase."""

import uuid
from dataclasses import dataclass
from datetime import UTC, datetime
from typing import Any

import pytest
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from app.main import create_app
from app.models import Appointment, AppointmentStatus, Doctor, Hospital, User, UserRole
from tests.api.helpers import auth_header, booking, future_slot, iso
from tests.conftest import client_with_session, make_settings
from tests.db.factories import make_appointment, make_doctor, make_hospital, make_user

URL = "/api/v1/appointments"
PAST_SLOT = datetime(2020, 1, 15, 9, 0, tzinfo=UTC)


@dataclass
class World:
    hospital_a: Hospital
    hospital_b: Hospital
    doctor1: Doctor  # visits A and B
    doctor2: Doctor  # visits A only
    admin: User
    doctor1_user: User


@pytest.fixture
def world(db_session: Session) -> World:
    hospital_a, hospital_b = make_hospital(db_session), make_hospital(db_session)
    doctor1 = make_doctor(db_session, [hospital_a, hospital_b])
    doctor2 = make_doctor(db_session, [hospital_a])
    return World(
        hospital_a=hospital_a,
        hospital_b=hospital_b,
        doctor1=doctor1,
        doctor2=doctor2,
        admin=make_user(db_session),
        doctor1_user=make_user(db_session, role=UserRole.DOCTOR, doctor=doctor1),
    )


def _field_errors(response_json: dict[str, Any]) -> list[str]:
    return [detail["field"] for detail in response_json["error"].get("details", [])]


# --- create -----------------------------------------------------------------------------------


def test_anonymous_booking_succeeds(
    db_client: TestClient, db_session: Session, world: World
) -> None:
    start = future_slot()
    response = db_client.post(
        URL,
        json=booking(world.doctor1, world.hospital_b, start, patient_name="  Jane Doe "),
    )
    assert response.status_code == 201
    body = response.json()
    assert response.headers["location"] == f"{URL}/{body['id']}"
    assert body["patient_name"] == "Jane Doe"
    assert body["status"] == "scheduled"
    assert body["start_time"] == iso(start)
    assert body["doctor"] == {
        "id": str(world.doctor1.id),
        "full_name": world.doctor1.full_name,
        "specialty": world.doctor1.specialty,
    }
    assert body["hospital"] == {"id": str(world.hospital_b.id), "name": world.hospital_b.name}
    stored = db_session.get(Appointment, uuid.UUID(body["id"]))
    assert stored is not None
    assert stored.created_by is None


def test_anonymous_booking_cannot_choose_a_status(db_client: TestClient, world: World) -> None:
    payload = booking(world.doctor1, world.hospital_a, future_slot(), status="confirmed")
    response = db_client.post(URL, json=payload)
    assert response.status_code == 422
    assert _field_errors(response.json()) == ["status"]

    explicit = booking(world.doctor1, world.hospital_a, future_slot(4), status="scheduled")
    assert db_client.post(URL, json=explicit).status_code == 201


def test_booking_the_same_slot_twice_is_a_conflict(db_client: TestClient, world: World) -> None:
    payload = booking(world.doctor1, world.hospital_a, future_slot())
    assert db_client.post(URL, json=payload).status_code == 201
    second = db_client.post(URL, json=payload)
    assert second.status_code == 409
    assert second.json()["error"]["code"] == "slot_conflict"


def test_a_doctor_cannot_be_double_booked_across_hospitals(
    db_client: TestClient, world: World
) -> None:
    start = future_slot()
    assert (
        db_client.post(URL, json=booking(world.doctor1, world.hospital_a, start)).status_code == 201
    )
    other_hospital = db_client.post(URL, json=booking(world.doctor1, world.hospital_b, start))
    assert other_hospital.status_code == 409


def test_a_cancelled_slot_can_be_booked_again(db_client: TestClient, world: World) -> None:
    start = future_slot()
    first = db_client.post(URL, json=booking(world.doctor1, world.hospital_a, start)).json()
    cancel = db_client.patch(
        f"{URL}/{first['id']}", json={"status": "cancelled"}, headers=auth_header(world.admin)
    )
    assert cancel.status_code == 200
    assert (
        db_client.post(URL, json=booking(world.doctor1, world.hospital_a, start)).status_code == 201
    )


def test_unknown_or_inactive_doctor_is_not_found(
    db_client: TestClient, db_session: Session, world: World
) -> None:
    unknown = booking(None, world.hospital_a, future_slot(), doctor_id=str(uuid.uuid4()))
    assert db_client.post(URL, json=unknown).status_code == 404

    world.doctor2.is_active = False
    db_session.flush()
    inactive = db_client.post(URL, json=booking(world.doctor2, world.hospital_a, future_slot()))
    assert inactive.status_code == 404


def test_hospital_must_be_one_the_doctor_visits(db_client: TestClient, world: World) -> None:
    response = db_client.post(URL, json=booking(world.doctor2, world.hospital_b, future_slot()))
    assert response.status_code == 422
    assert _field_errors(response.json()) == ["hospital_id"]

    missing = booking(world.doctor2, world.hospital_a, future_slot(), hospital_id=str(uuid.uuid4()))
    assert _field_errors(db_client.post(URL, json=missing).json()) == ["hospital_id"]


def test_past_and_far_future_times_are_rejected(db_client: TestClient, world: World) -> None:
    past = db_client.post(URL, json=booking(world.doctor1, world.hospital_a, PAST_SLOT))
    assert past.status_code == 422
    assert _field_errors(past.json()) == ["start_time"]

    too_far = db_client.post(URL, json=booking(world.doctor1, world.hospital_a, future_slot(800)))
    assert too_far.status_code == 422


def test_misaligned_start_time_is_a_validation_error(db_client: TestClient, world: World) -> None:
    response = db_client.post(
        URL, json=booking(world.doctor1, world.hospital_a, future_slot(minute=15))
    )
    assert response.status_code == 422
    assert _field_errors(response.json()) == ["start_time"]


def test_signed_in_doctor_books_for_themselves_by_default(
    db_client: TestClient, db_session: Session, world: World
) -> None:
    payload = booking(None, world.hospital_a, future_slot())
    response = db_client.post(URL, json=payload, headers=auth_header(world.doctor1_user))
    assert response.status_code == 201
    assert response.json()["doctor"]["id"] == str(world.doctor1.id)
    stored = db_session.get(Appointment, uuid.UUID(response.json()["id"]))
    assert stored is not None
    assert stored.created_by == world.doctor1_user.id


def test_signed_in_doctor_cannot_book_for_another_doctor(
    db_client: TestClient, world: World
) -> None:
    payload = booking(world.doctor2, world.hospital_a, future_slot())
    response = db_client.post(URL, json=payload, headers=auth_header(world.doctor1_user))
    assert response.status_code == 403
    assert response.json()["error"]["code"] == "forbidden"


def test_admin_can_book_for_any_doctor_and_set_a_status(
    db_client: TestClient, world: World
) -> None:
    payload = booking(world.doctor2, world.hospital_a, future_slot(), status="confirmed")
    response = db_client.post(URL, json=payload, headers=auth_header(world.admin))
    assert response.status_code == 201
    assert response.json()["status"] == "confirmed"


def test_admin_must_name_a_doctor(db_client: TestClient, world: World) -> None:
    payload = booking(None, world.hospital_a, future_slot())
    response = db_client.post(URL, json=payload, headers=auth_header(world.admin))
    assert response.status_code == 422
    assert _field_errors(response.json()) == ["doctor_id"]


def test_an_invalid_token_is_not_treated_as_anonymous(db_client: TestClient, world: World) -> None:
    payload = booking(world.doctor1, world.hospital_a, future_slot())
    response = db_client.post(URL, json=payload, headers={"Authorization": "Bearer garbage"})
    assert response.status_code == 401


def test_anonymous_booking_is_rate_limited(db_session: Session, world: World) -> None:
    app = create_app(make_settings(booking_rate_limit_per_minute=2))
    with client_with_session(app, db_session) as client:
        statuses = [
            client.post(
                URL, json=booking(world.doctor1, world.hospital_a, future_slot(days, 9, 0))
            ).status_code
            for days in (3, 4, 5)
        ]
        signed_in = client.post(
            URL,
            json=booking(world.doctor1, world.hospital_a, future_slot(6)),
            headers=auth_header(world.admin),
        )
    assert statuses == [201, 201, 429]
    assert signed_in.status_code == 201


# --- read, update, delete ---------------------------------------------------------------------


def test_anonymous_cannot_read_change_or_delete(db_client: TestClient, world: World) -> None:
    some_id = uuid.uuid4()
    assert db_client.get(f"{URL}/{some_id}").status_code == 401
    assert db_client.patch(f"{URL}/{some_id}", json={"status": "cancelled"}).status_code == 401
    assert db_client.delete(f"{URL}/{some_id}").status_code == 401


def test_get_returns_the_appointment(
    db_client: TestClient, db_session: Session, world: World
) -> None:
    appointment = make_appointment(db_session, world.doctor1, world.hospital_a, future_slot())
    response = db_client.get(f"{URL}/{appointment.id}", headers=auth_header(world.admin))
    assert response.status_code == 200
    assert response.json()["id"] == str(appointment.id)


def test_get_unknown_id_is_404_and_bad_id_is_422(db_client: TestClient, world: World) -> None:
    headers = auth_header(world.admin)
    assert db_client.get(f"{URL}/{uuid.uuid4()}", headers=headers).status_code == 404
    assert db_client.get(f"{URL}/not-a-uuid", headers=headers).status_code == 422


def test_a_doctor_only_sees_their_own_appointments(
    db_client: TestClient, db_session: Session, world: World
) -> None:
    own = make_appointment(db_session, world.doctor1, world.hospital_a, future_slot())
    others = make_appointment(db_session, world.doctor2, world.hospital_a, future_slot())
    headers = auth_header(world.doctor1_user)
    assert db_client.get(f"{URL}/{own.id}", headers=headers).status_code == 200
    assert db_client.get(f"{URL}/{others.id}", headers=headers).status_code == 404
    assert (
        db_client.patch(
            f"{URL}/{others.id}", json={"status": "cancelled"}, headers=headers
        ).status_code
        == 404
    )
    assert db_client.delete(f"{URL}/{others.id}", headers=headers).status_code == 404


def test_patch_changes_fields(db_client: TestClient, db_session: Session, world: World) -> None:
    appointment = make_appointment(db_session, world.doctor1, world.hospital_a, future_slot())
    new_start = future_slot(5, 10, 30)
    response = db_client.patch(
        f"{URL}/{appointment.id}",
        json={
            "patient_name": "John Smith",
            "hospital_id": str(world.hospital_b.id),
            "start_time": iso(new_start),
            "appointment_type": "follow_up",
            "status": "confirmed",
        },
        headers=auth_header(world.admin),
    )
    assert response.status_code == 200
    body = response.json()
    assert body["patient_name"] == "John Smith"
    assert body["hospital"]["id"] == str(world.hospital_b.id)
    assert body["start_time"] == iso(new_start)
    assert body["appointment_type"] == "follow_up"
    assert body["status"] == "confirmed"


def test_a_past_appointment_can_still_change_status(
    db_client: TestClient, db_session: Session, world: World
) -> None:
    appointment = make_appointment(db_session, world.doctor1, world.hospital_a, PAST_SLOT)
    headers = auth_header(world.admin)
    only_status = db_client.patch(
        f"{URL}/{appointment.id}", json={"status": "completed"}, headers=headers
    )
    assert only_status.status_code == 200
    unchanged_time = db_client.patch(
        f"{URL}/{appointment.id}",
        json={"start_time": iso(PAST_SLOT), "status": "no_show"},
        headers=headers,
    )
    assert unchanged_time.status_code == 200
    assert unchanged_time.json()["status"] == "no_show"


def test_moving_an_appointment_into_the_past_is_rejected(
    db_client: TestClient, db_session: Session, world: World
) -> None:
    appointment = make_appointment(db_session, world.doctor1, world.hospital_a, future_slot())
    response = db_client.patch(
        f"{URL}/{appointment.id}",
        json={"start_time": iso(PAST_SLOT)},
        headers=auth_header(world.admin),
    )
    assert response.status_code == 422
    assert _field_errors(response.json()) == ["start_time"]


def test_moving_onto_a_taken_slot_is_a_conflict(
    db_client: TestClient, db_session: Session, world: World
) -> None:
    taken = future_slot(3, 9, 0)
    make_appointment(db_session, world.doctor1, world.hospital_a, taken)
    movable = make_appointment(db_session, world.doctor1, world.hospital_a, future_slot(3, 9, 30))
    response = db_client.patch(
        f"{URL}/{movable.id}", json={"start_time": iso(taken)}, headers=auth_header(world.admin)
    )
    assert response.status_code == 409
    assert response.json()["error"]["code"] == "slot_conflict"


def test_reactivating_a_cancelled_appointment_can_conflict(
    db_client: TestClient, db_session: Session, world: World
) -> None:
    slot = future_slot()
    cancelled = make_appointment(
        db_session, world.doctor1, world.hospital_a, slot, status=AppointmentStatus.CANCELLED
    )
    make_appointment(db_session, world.doctor1, world.hospital_a, slot)
    response = db_client.patch(
        f"{URL}/{cancelled.id}", json={"status": "scheduled"}, headers=auth_header(world.admin)
    )
    assert response.status_code == 409


def test_patch_validates_hospital_and_doctor(
    db_client: TestClient, db_session: Session, world: World
) -> None:
    appointment = make_appointment(db_session, world.doctor2, world.hospital_a, future_slot())
    headers = auth_header(world.admin)
    wrong_hospital = db_client.patch(
        f"{URL}/{appointment.id}", json={"hospital_id": str(world.hospital_b.id)}, headers=headers
    )
    assert wrong_hospital.status_code == 422
    assert _field_errors(wrong_hospital.json()) == ["hospital_id"]

    unknown_doctor = db_client.patch(
        f"{URL}/{appointment.id}", json={"doctor_id": str(uuid.uuid4())}, headers=headers
    )
    assert unknown_doctor.status_code == 404


def test_a_doctor_cannot_hand_an_appointment_to_another_doctor(
    db_client: TestClient, db_session: Session, world: World
) -> None:
    appointment = make_appointment(db_session, world.doctor1, world.hospital_a, future_slot())
    response = db_client.patch(
        f"{URL}/{appointment.id}",
        json={"doctor_id": str(world.doctor2.id)},
        headers=auth_header(world.doctor1_user),
    )
    assert response.status_code == 403


def test_patch_rejects_empty_nulls_and_unknown_fields(
    db_client: TestClient, db_session: Session, world: World
) -> None:
    appointment = make_appointment(db_session, world.doctor1, world.hospital_a, future_slot())
    headers = auth_header(world.admin)
    assert db_client.patch(f"{URL}/{appointment.id}", json={}, headers=headers).status_code == 422
    null_status = db_client.patch(f"{URL}/{appointment.id}", json={"status": None}, headers=headers)
    assert null_status.status_code == 422
    assert _field_errors(null_status.json()) == ["status"]
    extra = db_client.patch(f"{URL}/{appointment.id}", json={"deleted_at": None}, headers=headers)
    assert extra.status_code == 422


def test_delete_is_soft_and_frees_the_slot(
    db_client: TestClient, db_session: Session, world: World
) -> None:
    slot = future_slot()
    appointment = make_appointment(db_session, world.doctor1, world.hospital_a, slot)
    headers = auth_header(world.admin)

    response = db_client.delete(f"{URL}/{appointment.id}", headers=headers)
    assert response.status_code == 204
    assert response.content == b""
    assert db_client.get(f"{URL}/{appointment.id}", headers=headers).status_code == 404
    assert db_client.delete(f"{URL}/{appointment.id}", headers=headers).status_code == 404

    stored = db_session.get(Appointment, appointment.id)
    assert stored is not None
    assert stored.deleted_at is not None

    rebook = db_client.post(URL, json=booking(world.doctor1, world.hospital_a, slot))
    assert rebook.status_code == 201
