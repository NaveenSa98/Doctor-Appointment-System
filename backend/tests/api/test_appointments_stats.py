"""GET /appointments/stats: counts per status, with the same scoping as the list."""

from typing import Any

import pytest
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from app.models import AppointmentStatus, Doctor, User, UserRole
from tests.api.helpers import auth_header, future_slot, iso
from tests.db.factories import make_appointment, make_doctor, make_hospital, make_user

URL = "/api/v1/appointments/stats"
S = AppointmentStatus
ZERO = {status.value: 0 for status in S}


@pytest.fixture
def world(db_session: Session) -> dict[str, Any]:
    hospital = make_hospital(db_session)
    doctor1 = make_doctor(db_session, [hospital])
    doctor2 = make_doctor(db_session, [hospital])
    slots = iter(range(2, 40))

    def add(doctor: Doctor, status: AppointmentStatus, **fields: Any) -> None:
        make_appointment(
            db_session, doctor, hospital, future_slot(next(slots), 9, 0), status=status, **fields
        )

    add(doctor1, S.SCHEDULED)
    add(doctor1, S.SCHEDULED)
    add(doctor1, S.CONFIRMED)
    add(doctor2, S.CANCELLED)
    add(doctor2, S.SCHEDULED)
    add(doctor2, S.SCHEDULED, deleted_at=future_slot(1))  # soft-deleted: never counted
    return {
        "admin": make_user(db_session),
        "doctor1": doctor1,
        "doctor1_user": make_user(db_session, role=UserRole.DOCTOR, doctor=doctor1),
        "doctor2": doctor2,
    }


def _get(client: TestClient, user: User, params: Any = None) -> Any:
    return client.get(URL, params=params, headers=auth_header(user))


def test_stats_require_sign_in(db_client: TestClient) -> None:
    assert db_client.get(URL).status_code == 401


def test_admin_counts_every_status_and_skips_deleted_rows(
    db_client: TestClient, world: dict[str, Any]
) -> None:
    body = _get(db_client, world["admin"]).json()
    assert body["total"] == 5
    assert body["by_status"] == {**ZERO, "scheduled": 3, "confirmed": 1, "cancelled": 1}


def test_stats_with_no_appointments_are_all_zero(
    db_client: TestClient, db_session: Session
) -> None:
    body = _get(db_client, make_user(db_session)).json()
    assert body == {"total": 0, "by_status": ZERO}


def test_doctor_filter_narrows_the_counts(db_client: TestClient, world: dict[str, Any]) -> None:
    params = {"doctor_id": str(world["doctor2"].id)}
    body = _get(db_client, world["admin"], params).json()
    assert body["total"] == 2
    assert body["by_status"] == {**ZERO, "scheduled": 1, "cancelled": 1}


def test_a_doctor_only_counts_their_own_even_when_asking_for_another(
    db_client: TestClient, world: dict[str, Any]
) -> None:
    for params in (None, {"doctor_id": str(world["doctor2"].id)}):
        body = _get(db_client, world["doctor1_user"], params).json()
        assert body["total"] == 3
        assert body["by_status"] == {**ZERO, "scheduled": 2, "confirmed": 1}


def test_date_range_is_inclusive_from_and_exclusive_to(
    db_client: TestClient, world: dict[str, Any]
) -> None:
    params = {"date_from": iso(future_slot(2, 0, 0)), "date_to": iso(future_slot(4, 0, 0))}
    body = _get(db_client, world["admin"], params).json()
    assert body["total"] == 2  # the appointments on day +2 and day +3


def test_reversed_date_range_is_a_422(db_client: TestClient, world: dict[str, Any]) -> None:
    params = {"date_from": iso(future_slot(5)), "date_to": iso(future_slot(2))}
    response = _get(db_client, world["admin"], params)
    assert response.status_code == 422
    assert response.json()["error"]["code"] == "validation_error"


def test_unknown_parameters_are_rejected(db_client: TestClient, world: dict[str, Any]) -> None:
    assert _get(db_client, world["admin"], {"status": "scheduled"}).status_code == 422
