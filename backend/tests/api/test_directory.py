"""Public lookups: hospitals, doctors and availability. Runs against the test schema."""

import uuid
from datetime import timedelta

from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from app.models import AppointmentStatus
from tests.api.helpers import future_slot, iso
from tests.db.factories import make_appointment, make_doctor, make_hospital


def test_hospitals_are_public_and_sorted_by_name(
    db_client: TestClient, db_session: Session
) -> None:
    make_hospital(db_session, "Beta Hospital")
    make_hospital(db_session, "alpha Clinic")
    response = db_client.get("/api/v1/hospitals")
    assert response.status_code == 200
    assert [h["name"] for h in response.json()] == ["alpha Clinic", "Beta Hospital"]
    assert set(response.json()[0]) == {"id", "name"}


def test_hospitals_can_be_filtered_by_doctor(db_client: TestClient, db_session: Session) -> None:
    visited, other = make_hospital(db_session, "Visited"), make_hospital(db_session, "Other")
    doctor = make_doctor(db_session, [visited])
    make_doctor(db_session, [other])
    response = db_client.get("/api/v1/hospitals", params={"doctor_id": str(doctor.id)})
    assert [h["name"] for h in response.json()] == ["Visited"]


def test_doctors_are_public_with_their_hospitals(
    db_client: TestClient, db_session: Session
) -> None:
    hospital_b, hospital_a = (
        make_hospital(db_session, "B Hospital"),
        make_hospital(db_session, "A Hospital"),
    )
    doctor = make_doctor(db_session, [hospital_b, hospital_a], name="Dr. Visiting")
    response = db_client.get("/api/v1/doctors")
    assert response.status_code == 200
    [body] = response.json()
    assert set(body) == {"id", "full_name", "specialty", "hospitals"}
    assert body["id"] == str(doctor.id)
    assert [h["name"] for h in body["hospitals"]] == ["A Hospital", "B Hospital"]


def test_doctors_can_be_filtered_by_hospital_and_hide_inactive_ones(
    db_client: TestClient, db_session: Session
) -> None:
    here, elsewhere = make_hospital(db_session), make_hospital(db_session)
    present = make_doctor(db_session, [here])
    make_doctor(db_session, [elsewhere])
    gone = make_doctor(db_session, [here])
    gone.is_active = False
    db_session.flush()

    response = db_client.get("/api/v1/doctors", params={"hospital_id": str(here.id)})
    assert [d["id"] for d in response.json()] == [str(present.id)]


def _window(days: int = 3) -> dict[str, str]:
    start = future_slot(days, 0, 0)
    return {"date_from": iso(start), "date_to": iso(start + timedelta(days=1))}


def test_availability_lists_only_taken_start_times(
    db_client: TestClient, db_session: Session
) -> None:
    hospital = make_hospital(db_session)
    doctor, other_doctor = make_doctor(db_session, [hospital]), make_doctor(db_session, [hospital])
    taken = future_slot(3, 9, 0)
    make_appointment(db_session, doctor, hospital, taken)
    make_appointment(
        db_session, doctor, hospital, future_slot(3, 9, 30), status=AppointmentStatus.CANCELLED
    )
    make_appointment(db_session, doctor, hospital, future_slot(3, 10, 0), deleted_at=taken)
    make_appointment(
        db_session, doctor, hospital, future_slot(3, 10, 30), status=AppointmentStatus.CONFIRMED
    )
    make_appointment(db_session, doctor, hospital, future_slot(5, 9, 0))  # outside the window
    make_appointment(db_session, other_doctor, hospital, future_slot(3, 11, 0))

    response = db_client.get(f"/api/v1/doctors/{doctor.id}/availability", params=_window())
    assert response.status_code == 200
    body = response.json()
    assert set(body) == {"doctor_id", "taken"}
    assert body["taken"] == [iso(future_slot(3, 9, 0)), iso(future_slot(3, 10, 30))]


def test_availability_validates_the_window(db_client: TestClient, db_session: Session) -> None:
    doctor = make_doctor(db_session, [make_hospital(db_session)])
    url = f"/api/v1/doctors/{doctor.id}/availability"
    start = future_slot(3, 0, 0)

    too_long = {"date_from": iso(start), "date_to": iso(start + timedelta(days=8))}
    assert db_client.get(url, params=too_long).status_code == 422
    reversed_window = {"date_from": iso(start), "date_to": iso(start - timedelta(hours=1))}
    assert db_client.get(url, params=reversed_window).status_code == 422
    naive = {"date_from": "2030-01-15T00:00:00", "date_to": "2030-01-16T00:00:00"}
    assert db_client.get(url, params=naive).status_code == 422
    assert db_client.get(url).status_code == 422


def test_availability_for_an_unknown_or_inactive_doctor_is_404(
    db_client: TestClient, db_session: Session
) -> None:
    assert (
        db_client.get(f"/api/v1/doctors/{uuid.uuid4()}/availability", params=_window()).status_code
        == 404
    )
    doctor = make_doctor(db_session, [make_hospital(db_session)])
    doctor.is_active = False
    db_session.flush()
    assert (
        db_client.get(f"/api/v1/doctors/{doctor.id}/availability", params=_window()).status_code
        == 404
    )
