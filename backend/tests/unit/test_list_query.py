from typing import Any

import pytest
from pydantic import ValidationError

from app.models import AppointmentSort, AppointmentStatus, AppointmentType
from app.repositories.appointment_repository import escape_like
from app.schemas.appointment import AppointmentListQuery


def _query(**values: Any) -> AppointmentListQuery:
    return AppointmentListQuery(**values)


def test_defaults() -> None:
    query = _query()
    assert query.q is None
    assert query.status == []
    assert query.type == []
    assert query.sort is AppointmentSort.START_TIME
    assert (query.page, query.page_size) == (1, 20)


def test_repeated_values_and_enums_are_parsed() -> None:
    query = _query(status=["scheduled", "confirmed"], type=["check_up"], sort="-patient_name")
    assert query.status == [AppointmentStatus.SCHEDULED, AppointmentStatus.CONFIRMED]
    assert query.type == [AppointmentType.CHECK_UP]
    assert query.sort is AppointmentSort.PATIENT_NAME_DESC


def test_search_text_is_trimmed_and_blank_is_ignored() -> None:
    assert _query(q="  jane ").q == "jane"
    assert _query(q="   ").q is None
    assert _query(q="").q is None


def test_search_text_is_limited_to_100_characters() -> None:
    assert _query(q="x" * 100).q == "x" * 100
    with pytest.raises(ValidationError):
        _query(q="x" * 101)


@pytest.mark.parametrize(
    "values",
    [
        {"page": 0},
        {"page": -1},
        {"page_size": 0},
        {"page_size": 101},
        {"sort": "doctor"},
        {"status": ["archived"]},
        {"type": ["surgery"]},
        {"doctor_id": "not-a-uuid"},
        {"date_from": "2030-01-15T00:00:00"},  # no timezone
        {"unknown": "value"},
    ],
)
def test_invalid_values_are_rejected(values: dict[str, Any]) -> None:
    with pytest.raises(ValidationError):
        _query(**values)


def test_page_size_limits_are_inclusive() -> None:
    assert _query(page_size=1).page_size == 1
    assert _query(page_size=100).page_size == 100


def test_aware_dates_are_accepted() -> None:
    query = _query(date_from="2030-01-15T00:00:00Z", date_to="2030-01-16T05:30:00+05:30")
    assert query.date_from is not None and query.date_to is not None


def test_like_wildcards_are_escaped() -> None:
    assert escape_like("100%") == "100\\%"
    assert escape_like("a_b") == "a\\_b"
    assert escape_like("back\\slash") == "back\\\\slash"
    assert escape_like("plain") == "plain"
