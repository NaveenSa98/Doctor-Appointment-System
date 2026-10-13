"""Search, filter, sort and pagination of GET /appointments. Runs on the test schema."""

from dataclasses import dataclass
from datetime import datetime
from typing import Any

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import Engine, event
from sqlalchemy.orm import Session

from app.models import (
    Appointment,
    AppointmentStatus,
    AppointmentType,
    Doctor,
    Hospital,
    User,
    UserRole,
)
from tests.api.helpers import auth_header, future_slot, iso
from tests.db.factories import make_appointment, make_doctor, make_hospital, make_user

URL = "/api/v1/appointments"
S = AppointmentStatus
T = AppointmentType


@dataclass
class Dataset:
    hospital_a: Hospital
    hospital_b: Hospital
    doctor1: Doctor  # visits A and B
    doctor2: Doctor  # visits A only
    admin: User
    doctor1_user: User
    alice: Appointment
    bob: Appointment
    carol: Appointment
    dan: Appointment
    eve: Appointment
    deleted: Appointment

    @property
    def all_live(self) -> list[Appointment]:
        return [self.alice, self.bob, self.carol, self.dan, self.eve]


@pytest.fixture
def data(db_session: Session) -> Dataset:
    hospital_a, hospital_b = make_hospital(db_session), make_hospital(db_session)
    doctor1 = make_doctor(db_session, [hospital_a, hospital_b])
    doctor2 = make_doctor(db_session, [hospital_a])

    def add(
        name: str, doctor: Doctor, hospital: Hospital, when: datetime, **fields: Any
    ) -> Appointment:
        return make_appointment(db_session, doctor, hospital, when, patient_name=name, **fields)

    return Dataset(
        hospital_a=hospital_a,
        hospital_b=hospital_b,
        doctor1=doctor1,
        doctor2=doctor2,
        admin=make_user(db_session),
        doctor1_user=make_user(db_session, role=UserRole.DOCTOR, doctor=doctor1),
        alice=add(
            "Alice Anderson",
            doctor1,
            hospital_a,
            future_slot(2, 9, 0),
            appointment_type=T.CONSULTATION,
            status=S.SCHEDULED,
        ),
        bob=add(
            "bob Brown",
            doctor1,
            hospital_b,
            future_slot(2, 9, 30),
            appointment_type=T.FOLLOW_UP,
            status=S.CONFIRMED,
        ),
        carol=add(
            "Carol Anderson",
            doctor2,
            hospital_a,
            future_slot(3, 9, 0),
            appointment_type=T.CHECK_UP,
            status=S.SCHEDULED,
        ),
        dan=add(
            "Dan Clark",
            doctor2,
            hospital_a,
            future_slot(3, 10, 0),
            appointment_type=T.PROCEDURE,
            status=S.CANCELLED,
        ),
        eve=add(
            "Eve Davis",
            doctor1,
            hospital_a,
            future_slot(4, 9, 0),
            appointment_type=T.CONSULTATION,
            status=S.COMPLETED,
        ),
        deleted=add(
            "Zed Deleted", doctor1, hospital_a, future_slot(4, 10, 0), deleted_at=future_slot(1)
        ),
    )


def _get(client: TestClient, data: Dataset, params: Any = None) -> Any:
    return client.get(URL, params=params, headers=auth_header(data.admin))


def _ids(response: Any) -> list[str]:
    return [item["id"] for item in response.json()["items"]]


def _expect(*appointments: Appointment) -> list[str]:
    return [str(appointment.id) for appointment in appointments]


# --- access and shape -------------------------------------------------------------------------


def test_listing_requires_sign_in(db_client: TestClient) -> None:
    assert db_client.get(URL).status_code == 401


def test_default_list_is_ordered_by_start_time_and_hides_deleted_rows(
    db_client: TestClient, data: Dataset
) -> None:
    response = _get(db_client, data)
    assert response.status_code == 200
    body = response.json()
    assert _ids(response) == _expect(data.alice, data.bob, data.carol, data.dan, data.eve)
    assert (body["total"], body["page"], body["page_size"], body["pages"]) == (5, 1, 20, 1)
    assert set(body["items"][0]) == {
        "id",
        "patient_name",
        "doctor",
        "hospital",
        "start_time",
        "appointment_type",
        "status",
        "created_at",
        "updated_at",
    }


# --- filters ----------------------------------------------------------------------------------


def test_search_matches_substrings_ignoring_case_and_spaces(
    db_client: TestClient, data: Dataset
) -> None:
    for text in ("anderson", "ANDERSON", "  Anderson  ", "nders"):
        assert _ids(_get(db_client, data, {"q": text})) == _expect(data.alice, data.carol)
    assert _ids(_get(db_client, data, {"q": "an"})) == _expect(data.alice, data.carol, data.dan)
    assert _ids(_get(db_client, data, {"q": "no-such-patient"})) == []


def test_blank_search_means_no_search(db_client: TestClient, data: Dataset) -> None:
    assert _get(db_client, data, {"q": "   "}).json()["total"] == 5


def test_search_treats_wildcards_literally(
    db_client: TestClient, db_session: Session, data: Dataset
) -> None:
    percent = make_appointment(
        db_session, data.doctor1, data.hospital_a, future_slot(6, 9, 0), patient_name="100% Sure"
    )
    make_appointment(
        db_session, data.doctor1, data.hospital_a, future_slot(6, 9, 30), patient_name="100X Sure"
    )
    underscore = make_appointment(
        db_session, data.doctor1, data.hospital_a, future_slot(6, 10, 0), patient_name="a_b Name"
    )
    make_appointment(
        db_session, data.doctor1, data.hospital_a, future_slot(6, 10, 30), patient_name="axb Name"
    )
    backslash = make_appointment(
        db_session, data.doctor1, data.hospital_a, future_slot(6, 11, 0), patient_name="back\\slash"
    )

    assert _ids(_get(db_client, data, {"q": "100%"})) == _expect(percent)
    assert _ids(_get(db_client, data, {"q": "a_b"})) == _expect(underscore)
    assert _ids(_get(db_client, data, {"q": "_"})) == _expect(underscore)
    assert _ids(_get(db_client, data, {"q": "\\"})) == _expect(backslash)
    assert _ids(_get(db_client, data, {"q": "%"})) == _expect(percent)


def test_filter_by_doctor_and_hospital(db_client: TestClient, data: Dataset) -> None:
    by_doctor = _get(db_client, data, {"doctor_id": str(data.doctor2.id)})
    assert _ids(by_doctor) == _expect(data.carol, data.dan)
    by_hospital = _get(db_client, data, {"hospital_id": str(data.hospital_b.id)})
    assert _ids(by_hospital) == _expect(data.bob)


def test_filter_by_one_or_several_statuses(db_client: TestClient, data: Dataset) -> None:
    assert _ids(_get(db_client, data, {"status": "cancelled"})) == _expect(data.dan)
    several = _get(db_client, data, {"status": ["scheduled", "confirmed"]})
    assert _ids(several) == _expect(data.alice, data.bob, data.carol)


def test_filter_by_one_or_several_types(db_client: TestClient, data: Dataset) -> None:
    several = _get(db_client, data, {"type": ["consultation", "check_up"]})
    assert _ids(several) == _expect(data.alice, data.carol, data.eve)
    assert _ids(_get(db_client, data, {"type": "procedure"})) == _expect(data.dan)


def test_date_range_is_inclusive_at_the_start_and_exclusive_at_the_end(
    db_client: TestClient, data: Dataset
) -> None:
    start = data.alice.start_time
    end = data.bob.start_time
    both = _get(db_client, data, {"date_from": iso(start), "date_to": iso(end)})
    assert _ids(both) == _expect(data.alice)

    day = future_slot(3, 0, 0)
    next_day = future_slot(4, 0, 0)
    one_day = _get(db_client, data, {"date_from": iso(day), "date_to": iso(next_day)})
    assert _ids(one_day) == _expect(data.carol, data.dan)

    only_from = _get(db_client, data, {"date_from": iso(next_day)})
    assert _ids(only_from) == _expect(data.eve)
    only_to = _get(db_client, data, {"date_to": iso(day)})
    assert _ids(only_to) == _expect(data.alice, data.bob)


def test_filters_combine(db_client: TestClient, data: Dataset) -> None:
    response = _get(
        db_client,
        data,
        {
            "q": "anderson",
            "doctor_id": str(data.doctor2.id),
            "status": "scheduled",
            "type": "check_up",
        },
    )
    assert _ids(response) == _expect(data.carol)
    nothing = _get(db_client, data, {"q": "anderson", "status": "cancelled"})
    assert nothing.status_code == 200
    assert nothing.json() == {"items": [], "total": 0, "page": 1, "page_size": 20, "pages": 0}


# --- sorting ----------------------------------------------------------------------------------


def test_sort_orders(db_client: TestClient, data: Dataset) -> None:
    ordered = {
        "start_time": [data.alice, data.bob, data.carol, data.dan, data.eve],
        "-start_time": [data.eve, data.dan, data.carol, data.bob, data.alice],
        "patient_name": [data.alice, data.bob, data.carol, data.dan, data.eve],
        "-patient_name": [data.eve, data.dan, data.carol, data.bob, data.alice],
    }
    for sort, expected in ordered.items():
        assert _ids(_get(db_client, data, {"sort": sort})) == _expect(*expected), sort


def test_created_at_sorts_are_accepted(db_client: TestClient, data: Dataset) -> None:
    for sort in ("created_at", "-created_at"):
        response = _get(db_client, data, {"sort": sort})
        assert response.status_code == 200
        assert sorted(_ids(response)) == sorted(_expect(*data.all_live))


def test_ties_are_broken_by_id_so_pages_are_stable(db_client: TestClient, data: Dataset) -> None:
    # Every row was created in one transaction, so created_at is identical for all of them.
    seen: list[str] = []
    for page in (1, 2, 3):
        response = _get(db_client, data, {"sort": "created_at", "page": page, "page_size": 2})
        seen.extend(_ids(response))
    assert len(seen) == 5
    assert sorted(seen) == sorted(_expect(*data.all_live))
    assert seen == sorted(seen)  # ties fall back to ascending id


# --- pagination -------------------------------------------------------------------------------


def test_pagination_pages_and_totals(db_client: TestClient, data: Dataset) -> None:
    first = _get(db_client, data, {"page_size": 2}).json()
    assert (first["total"], first["pages"], len(first["items"])) == (5, 3, 2)
    last = _get(db_client, data, {"page_size": 2, "page": 3})
    assert _ids(last) == _expect(data.eve)
    assert last.json()["page"] == 3


def test_a_page_past_the_end_is_empty_but_keeps_the_totals(
    db_client: TestClient, data: Dataset
) -> None:
    body = _get(db_client, data, {"page_size": 2, "page": 9}).json()
    assert body["items"] == []
    assert (body["total"], body["pages"], body["page"]) == (5, 3, 9)


@pytest.mark.parametrize(
    "params",
    [
        {"page_size": 101},
        {"page_size": 0},
        {"page": 0},
        {"sort": "doctor"},
        {"status": "archived"},
        {"type": "surgery"},
        {"doctor_id": "nope"},
        {"date_from": "2030-01-15T00:00:00"},
        {"surprise": "1"},
    ],
)
def test_invalid_query_parameters_are_rejected(
    db_client: TestClient, data: Dataset, params: dict[str, Any]
) -> None:
    response = _get(db_client, data, params)
    assert response.status_code == 422
    assert response.json()["error"]["code"] == "validation_error"


def test_a_reversed_date_range_is_rejected(db_client: TestClient, data: Dataset) -> None:
    params = {"date_from": iso(future_slot(5, 0, 0)), "date_to": iso(future_slot(2, 0, 0))}
    response = _get(db_client, data, params)
    assert response.status_code == 422
    assert response.json()["error"]["details"][0]["field"] == "date_to"


# --- doctor scoping ---------------------------------------------------------------------------


def test_a_doctor_only_lists_their_own_appointments(db_client: TestClient, data: Dataset) -> None:
    headers = auth_header(data.doctor1_user)
    response = db_client.get(URL, headers=headers)
    assert _ids(response) == _expect(data.alice, data.bob, data.eve)
    assert response.json()["total"] == 3

    # Asking for another doctor's appointments does not widen the result.
    other = db_client.get(URL, params={"doctor_id": str(data.doctor2.id)}, headers=headers)
    assert _ids(other) == _expect(data.alice, data.bob, data.eve)
    searched = db_client.get(URL, params={"q": "anderson"}, headers=headers)
    assert _ids(searched) == _expect(data.alice)


# --- queries ----------------------------------------------------------------------------------


def test_the_number_of_queries_does_not_grow_with_the_page_size(
    db_client: TestClient, migrated_engine: Engine, data: Dataset
) -> None:
    statements: list[str] = []

    def record(_conn: Any, _cursor: Any, statement: str, *_args: Any) -> None:
        statements.append(statement)

    def queries_for(page_size: int) -> int:
        statements.clear()
        event.listen(migrated_engine, "before_cursor_execute", record)
        try:
            assert _get(db_client, data, {"page_size": page_size}).status_code == 200
        finally:
            event.remove(migrated_engine, "before_cursor_execute", record)
        return len(statements)

    one_row = queries_for(1)
    five_rows = queries_for(20)
    assert one_row == five_rows
    assert five_rows <= 3  # the signed-in user, the count and the page
