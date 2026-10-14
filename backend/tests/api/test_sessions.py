"""Weekly doctor sessions: admin changes, bookable slots and booking enforcement."""

from dataclasses import dataclass
from datetime import UTC, date, datetime, time, timedelta
from typing import Any

import pytest
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from app.core.clock import utcnow
from app.models import AppointmentStatus, Doctor, Hospital, User, UserRole
from tests.api.helpers import auth_header, booking, iso
from tests.db.factories import make_appointment, make_doctor, make_hospital, make_user

ADMIN = "/api/v1/admin"
DOCTORS = "/api/v1/doctors"
APPOINTMENTS = "/api/v1/appointments"


@dataclass
class World:
    admin: User
    hospital_a: Hospital
    hospital_b: Hospital
    doctor: Doctor

    @property
    def headers(self) -> dict[str, str]:
        return auth_header(self.admin)


@pytest.fixture
def world(db_session: Session) -> World:
    hospital_a = make_hospital(db_session, "Alpha Hospital")
    hospital_b = make_hospital(db_session, "Beta Clinic")
    return World(
        admin=make_user(db_session),
        hospital_a=hospital_a,
        hospital_b=hospital_b,
        doctor=make_doctor(db_session, [hospital_a, hospital_b]),
    )


def next_day(weekday: int, at_least_days: int = 3) -> date:
    """The next date (clinic offset is 0 in tests, so UTC) falling on this weekday."""
    day = (utcnow() + timedelta(days=at_least_days)).date()
    while day.weekday() != weekday:
        day += timedelta(days=1)
    return day


def at(day: date, hour: int, minute: int = 0) -> datetime:
    return datetime.combine(day, time(hour, minute), tzinfo=UTC)


def add_session(
    client: TestClient,
    world: World,
    hospital: Hospital | None = None,
    weekday: int = 0,
    start: str = "09:00",
    end: str = "12:00",
) -> Any:
    body = {
        "hospital_id": str((hospital or world.hospital_a).id),
        "weekday": weekday,
        "start_time": start,
        "end_time": end,
    }
    return client.post(
        f"{ADMIN}/doctors/{world.doctor.id}/sessions", json=body, headers=world.headers
    )


def slots_for(client: TestClient, world: World, day: date, hospital: Hospital | None = None) -> Any:
    params = {
        "hospital_id": str((hospital or world.hospital_a).id),
        "date_from": iso(at(day, 0)),
        "date_to": iso(at(day + timedelta(days=1), 0)),
    }
    return client.get(f"{DOCTORS}/{world.doctor.id}/slots", params=params)


def book(
    client: TestClient, world: World, start: datetime, hospital: Hospital | None = None
) -> Any:
    body = booking(world.doctor, hospital or world.hospital_a, start)
    return client.post(APPOINTMENTS, json=body, headers=world.headers)


# ---- creating and listing ----------------------------------------------------------------------


def test_create_a_session_and_read_the_schedule(db_client: TestClient, world: World) -> None:
    response = add_session(db_client, world, weekday=2, start="13:30", end="17:00")
    assert response.status_code == 201
    body = response.json()
    assert (body["weekday"], body["start_time"], body["end_time"]) == (2, "13:30", "17:00")
    assert body["hospital"]["name"] == "Alpha Hospital"
    assert body["skipped"] == []

    add_session(db_client, world, weekday=0)
    schedule = db_client.get(f"{DOCTORS}/{world.doctor.id}/sessions", headers=world.headers).json()
    assert schedule["utc_offset_minutes"] == 0
    assert [s["weekday"] for s in schedule["sessions"]] == [0, 2]  # ordered by weekday


@pytest.mark.parametrize(
    "overrides",
    [
        {"start_time": "12:00", "end_time": "09:00"},
        {"start_time": "09:00", "end_time": "09:00"},
        {"start_time": "09:15"},
        {"weekday": 7},
        {"day": "monday"},
    ],
)
def test_invalid_sessions_are_422(
    db_client: TestClient, world: World, overrides: dict[str, Any]
) -> None:
    body = {
        "hospital_id": str(world.hospital_a.id),
        "weekday": 0,
        "start_time": "09:00",
        "end_time": "12:00",
    } | overrides
    response = db_client.post(
        f"{ADMIN}/doctors/{world.doctor.id}/sessions", json=body, headers=world.headers
    )
    assert response.status_code == 422


def test_a_session_must_be_at_a_hospital_the_doctor_visits(
    db_client: TestClient, world: World, db_session: Session
) -> None:
    elsewhere = make_hospital(db_session, "Gamma Centre")
    response = add_session(db_client, world, hospital=elsewhere)
    assert response.status_code == 422
    assert response.json()["error"]["details"][0]["field"] == "hospital_id"


def test_sessions_of_one_doctor_cannot_overlap_even_at_another_hospital(
    db_client: TestClient, world: World
) -> None:
    assert add_session(db_client, world, weekday=0, start="09:00", end="12:00").status_code == 201
    clash = add_session(db_client, world, hospital=world.hospital_b, start="11:30", end="14:00")
    assert clash.status_code == 409
    assert clash.json()["error"]["code"] == "session_overlap"

    assert add_session(db_client, world, start="12:00", end="14:00").status_code == 201  # touching
    assert add_session(db_client, world, weekday=1, start="09:00", end="12:00").status_code == 201


def test_only_admins_change_sessions_and_only_the_doctor_reads_their_own(
    db_client: TestClient, world: World, db_session: Session
) -> None:
    mine = make_user(db_session, role=UserRole.DOCTOR, doctor=world.doctor)
    other_doctor = make_doctor(db_session, [world.hospital_a])
    theirs = make_user(db_session, role=UserRole.DOCTOR, doctor=other_doctor)
    patient = make_user(db_session, role=UserRole.PATIENT)
    body = {
        "hospital_id": str(world.hospital_a.id),
        "weekday": 0,
        "start_time": "09:00",
        "end_time": "10:00",
    }

    create_url = f"{ADMIN}/doctors/{world.doctor.id}/sessions"
    assert db_client.post(create_url, json=body, headers=auth_header(mine)).status_code == 403
    assert db_client.post(create_url, json=body).status_code == 401

    read_url = f"{DOCTORS}/{world.doctor.id}/sessions"
    assert db_client.get(read_url).status_code == 401
    assert db_client.get(read_url, headers=auth_header(mine)).status_code == 200
    assert db_client.get(read_url, headers=auth_header(theirs)).status_code == 403
    assert db_client.get(read_url, headers=auth_header(patient)).status_code == 403
    assert db_client.get(read_url, headers=world.headers).status_code == 200


# ---- slots and booking -------------------------------------------------------------------------


def test_slots_follow_the_sessions(db_client: TestClient, world: World) -> None:
    add_session(db_client, world, weekday=0, start="09:00", end="12:00")
    monday = next_day(0)

    body = slots_for(db_client, world, monday).json()  # public: no token
    assert body["restricted"] is True
    assert body["slots"][0] == iso(at(monday, 9))
    assert body["slots"][-1] == iso(at(monday, 11, 30))
    assert len(body["slots"]) == 6

    assert slots_for(db_client, world, monday + timedelta(days=1)).json()["slots"] == []
    other = slots_for(db_client, world, monday, hospital=world.hospital_b).json()
    assert other["restricted"] is True
    assert other["slots"] == []


def test_a_doctor_without_sessions_is_unrestricted(db_client: TestClient, world: World) -> None:
    body = slots_for(db_client, world, next_day(0)).json()
    assert body == {
        "doctor_id": str(world.doctor.id),
        "hospital_id": str(world.hospital_a.id),
        "restricted": False,
        "slots": [],
    }
    assert book(db_client, world, at(next_day(3), 20, 30)).status_code == 201  # any time


def test_slots_window_rules(db_client: TestClient, world: World) -> None:
    url = f"{DOCTORS}/{world.doctor.id}/slots"
    base = {"hospital_id": str(world.hospital_a.id)}
    too_long = {**base, "date_from": "2030-01-01T00:00:00Z", "date_to": "2030-01-20T00:00:00Z"}
    naive = {**base, "date_from": "2030-01-01T00:00:00", "date_to": "2030-01-02T00:00:00"}
    assert db_client.get(url, params=too_long).status_code == 422
    assert db_client.get(url, params=naive).status_code == 422
    assert db_client.get(url, params=base).status_code == 422


def test_booking_is_only_possible_inside_a_session(db_client: TestClient, world: World) -> None:
    add_session(db_client, world, weekday=0, start="09:00", end="12:00")
    monday = next_day(0)

    assert book(db_client, world, at(monday, 11, 30)).status_code == 201  # the last slot
    for outside in (at(monday, 12), at(monday, 8, 30), at(next_day(1), 9)):
        response = book(db_client, world, outside)
        assert response.status_code == 422
        assert response.json()["error"]["details"][0]["field"] == "start_time"
    assert (
        book(db_client, world, at(monday + timedelta(days=7), 9), world.hospital_b).status_code
        == 422
    )


def test_moving_a_booking_outside_the_sessions_is_refused(
    db_client: TestClient, world: World
) -> None:
    add_session(db_client, world, weekday=0, start="09:00", end="12:00")
    monday = next_day(0)
    created = book(db_client, world, at(monday, 9)).json()

    bad = db_client.patch(
        f"{APPOINTMENTS}/{created['id']}",
        json={"start_time": iso(at(monday, 15))},
        headers=world.headers,
    )
    assert bad.status_code == 422
    ok = db_client.patch(
        f"{APPOINTMENTS}/{created['id']}",
        json={"start_time": iso(at(monday, 10))},
        headers=world.headers,
    )
    assert ok.status_code == 200
    status_only = db_client.patch(
        f"{APPOINTMENTS}/{created['id']}", json={"status": "confirmed"}, headers=world.headers
    )
    assert status_only.status_code == 200  # untouched time is never re-checked


# ---- skipping a day ----------------------------------------------------------------------------


def test_skip_and_restore_a_day(db_client: TestClient, world: World) -> None:
    session_id = add_session(db_client, world, weekday=0).json()["id"]
    monday = next_day(0)
    url = f"{ADMIN}/sessions/{session_id}/skipped-dates"

    skipped = db_client.post(
        url, json={"date": monday.isoformat(), "reason": "Leave"}, headers=world.headers
    )
    assert skipped.status_code == 201
    assert skipped.json()["skipped"] == [{"on_date": monday.isoformat(), "reason": "Leave"}]
    assert slots_for(db_client, world, monday).json()["slots"] == []
    assert book(db_client, world, at(monday, 9)).status_code == 422

    again = db_client.post(url, json={"date": monday.isoformat()}, headers=world.headers)
    assert again.status_code == 409

    restored = db_client.delete(f"{url}/{monday.isoformat()}", headers=world.headers)
    assert restored.status_code == 200
    assert restored.json()["skipped"] == []
    assert book(db_client, world, at(monday, 9)).status_code == 201

    missing = db_client.delete(f"{url}/{monday.isoformat()}", headers=world.headers)
    assert missing.status_code == 404


def test_skip_rejects_the_past_and_the_wrong_weekday(db_client: TestClient, world: World) -> None:
    session_id = add_session(db_client, world, weekday=0).json()["id"]
    url = f"{ADMIN}/sessions/{session_id}/skipped-dates"
    past = next_day(0) - timedelta(days=21)
    wrong_day = next_day(1)
    for day in (past, wrong_day):
        response = db_client.post(url, json={"date": day.isoformat()}, headers=world.headers)
        assert response.status_code == 422


# ---- changing and removing sessions -----------------------------------------------------------


def test_changes_that_would_strand_bookings_are_refused(
    db_client: TestClient, world: World, db_session: Session
) -> None:
    session_id = add_session(db_client, world, weekday=0, start="09:00", end="12:00").json()["id"]
    monday = next_day(0)
    make_appointment(db_session, world.doctor, world.hospital_a, at(monday, 11))

    def code(response: Any) -> str:
        return response.json()["error"]["code"]

    delete = db_client.delete(f"{ADMIN}/sessions/{session_id}", headers=world.headers)
    assert (delete.status_code, code(delete)) == (409, "session_has_appointments")

    skip = db_client.post(
        f"{ADMIN}/sessions/{session_id}/skipped-dates",
        json={"date": monday.isoformat()},
        headers=world.headers,
    )
    assert (skip.status_code, code(skip)) == (409, "session_has_appointments")

    shrink = db_client.patch(
        f"{ADMIN}/sessions/{session_id}", json={"end_time": "10:30"}, headers=world.headers
    )
    assert shrink.status_code == 409
    move = db_client.patch(
        f"{ADMIN}/sessions/{session_id}", json={"weekday": 3}, headers=world.headers
    )
    assert move.status_code == 409

    extend = db_client.patch(
        f"{ADMIN}/sessions/{session_id}", json={"end_time": "13:00"}, headers=world.headers
    )
    assert extend.status_code == 200  # nothing is stranded


def test_a_cancelled_booking_does_not_block_removing_a_session(
    db_client: TestClient, world: World, db_session: Session
) -> None:
    session_id = add_session(db_client, world, weekday=0).json()["id"]
    make_appointment(
        db_session,
        world.doctor,
        world.hospital_a,
        at(next_day(0), 9),
        status=AppointmentStatus.CANCELLED,
    )
    assert (
        db_client.delete(f"{ADMIN}/sessions/{session_id}", headers=world.headers).status_code == 204
    )


def test_removing_the_last_session_makes_the_doctor_unrestricted_again(
    db_client: TestClient, world: World
) -> None:
    session_id = add_session(db_client, world, weekday=0).json()["id"]
    assert book(db_client, world, at(next_day(3), 20)).status_code == 422

    assert (
        db_client.delete(f"{ADMIN}/sessions/{session_id}", headers=world.headers).status_code == 204
    )
    assert book(db_client, world, at(next_day(3), 20)).status_code == 201


def test_moving_a_session_to_another_weekday_clears_its_skipped_days(
    db_client: TestClient, world: World
) -> None:
    session_id = add_session(db_client, world, weekday=0).json()["id"]
    db_client.post(
        f"{ADMIN}/sessions/{session_id}/skipped-dates",
        json={"date": next_day(0).isoformat()},
        headers=world.headers,
    )
    moved = db_client.patch(
        f"{ADMIN}/sessions/{session_id}", json={"weekday": 4}, headers=world.headers
    )
    assert moved.status_code == 200
    assert (moved.json()["weekday"], moved.json()["skipped"]) == (4, [])


def test_update_validation_and_unknown_ids(db_client: TestClient, world: World) -> None:
    session_id = add_session(db_client, world, start="09:00", end="12:00").json()["id"]
    url = f"{ADMIN}/sessions/{session_id}"
    assert db_client.patch(url, json={}, headers=world.headers).status_code == 422
    assert (
        db_client.patch(url, json={"end_time": "08:00"}, headers=world.headers).status_code == 422
    )
    unknown = "00000000-0000-0000-0000-000000000000"
    assert (
        db_client.patch(
            f"{ADMIN}/sessions/{unknown}", json={"weekday": 1}, headers=world.headers
        ).status_code
        == 404
    )
    assert db_client.delete(f"{ADMIN}/sessions/{unknown}", headers=world.headers).status_code == 404


def test_a_hospital_with_sessions_cannot_be_removed_from_the_doctor(
    db_client: TestClient, world: World
) -> None:
    add_session(db_client, world, hospital=world.hospital_b)
    response = db_client.patch(
        f"{ADMIN}/doctors/{world.doctor.id}",
        json={"hospital_ids": [str(world.hospital_a.id)]},
        headers=world.headers,
    )
    assert response.status_code == 409
    assert response.json()["error"]["code"] == "hospital_has_sessions"
