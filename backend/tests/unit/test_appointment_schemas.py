import uuid
from datetime import UTC, datetime
from typing import Any

import pytest
from pydantic import ValidationError

from app.models import AppointmentStatus, AppointmentType
from app.schemas.appointment import AppointmentCreate, AppointmentUpdate

HOSPITAL = str(uuid.uuid4())


def _create(**overrides: Any) -> AppointmentCreate:
    values: dict[str, Any] = {
        "patient_name": "Jane Doe",
        "hospital_id": HOSPITAL,
        "start_time": "2030-01-15T09:00:00Z",
        "appointment_type": "consultation",
    }
    values.update(overrides)
    return AppointmentCreate(**values)


def _fields_with_errors(exc: pytest.ExceptionInfo[ValidationError]) -> set[str]:
    return {str(error["loc"][0]) for error in exc.value.errors()}


def test_valid_create_parses_with_defaults() -> None:
    data = _create()
    assert data.patient_name == "Jane Doe"
    assert data.doctor_id is None
    assert data.status is None
    assert data.appointment_type is AppointmentType.CONSULTATION
    assert data.start_time == datetime(2030, 1, 15, 9, 0, tzinfo=UTC)


def test_patient_name_is_trimmed() -> None:
    assert _create(patient_name="  Jane Doe  ").patient_name == "Jane Doe"


@pytest.mark.parametrize("name", ["", " a ", "x" * 101, "Jane\nDoe", "Jane\x00Doe", "Jane\tDoe"])
def test_bad_patient_names_are_rejected(name: str) -> None:
    with pytest.raises(ValidationError) as exc:
        _create(patient_name=name)
    assert "patient_name" in _fields_with_errors(exc)


def test_unicode_names_are_allowed() -> None:
    assert _create(patient_name="Sanduni Gunawardena").patient_name == "Sanduni Gunawardena"
    assert _create(patient_name="Zoë O'Brien-Smith").patient_name == "Zoë O'Brien-Smith"


def test_start_time_is_normalised_to_utc() -> None:
    data = _create(start_time="2030-01-15T14:30:00+05:30")
    assert data.start_time == datetime(2030, 1, 15, 9, 0, tzinfo=UTC)
    assert data.start_time.utcoffset() == UTC.utcoffset(None)


@pytest.mark.parametrize(
    "start_time",
    [
        "2030-01-15T09:00:00",  # no timezone
        "2030-01-15T09:15:00Z",  # not on the half hour
        "2030-01-15T09:00:05Z",  # seconds
        "2030-01-15T09:00:00.5Z",  # microseconds
        "not-a-date",
    ],
)
def test_bad_start_times_are_rejected(start_time: str) -> None:
    with pytest.raises(ValidationError) as exc:
        _create(start_time=start_time)
    assert "start_time" in _fields_with_errors(exc)


def test_half_hour_start_is_accepted() -> None:
    assert _create(start_time="2030-01-15T09:30:00Z").start_time.minute == 30


def test_unknown_fields_and_bad_enums_are_rejected() -> None:
    with pytest.raises(ValidationError):
        _create(created_by=str(uuid.uuid4()))
    with pytest.raises(ValidationError):
        _create(appointment_type="surgery")
    with pytest.raises(ValidationError):
        _create(status="archived")


def test_status_can_be_provided() -> None:
    assert _create(status="confirmed").status is AppointmentStatus.CONFIRMED


def test_update_accepts_any_subset() -> None:
    data = AppointmentUpdate(status="completed")
    assert data.model_dump(exclude_unset=True) == {"status": AppointmentStatus.COMPLETED}


def test_update_requires_at_least_one_field() -> None:
    with pytest.raises(ValidationError):
        AppointmentUpdate()


@pytest.mark.parametrize(
    "field",
    ["patient_name", "doctor_id", "hospital_id", "start_time", "appointment_type", "status"],
)
def test_update_rejects_explicit_nulls(field: str) -> None:
    with pytest.raises(ValidationError) as exc:
        AppointmentUpdate(**{field: None})
    assert field in _fields_with_errors(exc)


def test_update_applies_the_same_field_rules() -> None:
    with pytest.raises(ValidationError):
        AppointmentUpdate(start_time="2030-01-15T09:10:00Z")
    with pytest.raises(ValidationError):
        AppointmentUpdate(patient_name="x")
    with pytest.raises(ValidationError):
        AppointmentUpdate(unknown="value")
