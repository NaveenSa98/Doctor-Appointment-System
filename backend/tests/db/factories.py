"""Small helpers that create valid rows for database tests."""

import uuid
from collections.abc import Iterator, Sequence
from contextlib import contextmanager
from datetime import UTC, datetime
from typing import Any

import pytest
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.core.security import hash_password
from app.models import (
    Appointment,
    AppointmentStatus,
    AppointmentType,
    Doctor,
    Hospital,
    User,
    UserRole,
)

SLOT = datetime(2030, 1, 15, 9, 0, tzinfo=UTC)


def _unique(prefix: str) -> str:
    return f"{prefix}-{uuid.uuid4().hex[:8]}"


def make_hospital(session: Session, name: str | None = None) -> Hospital:
    hospital = Hospital(name=name or _unique("Hospital"))
    session.add(hospital)
    session.flush()
    return hospital


def make_doctor(session: Session, hospitals: Sequence[Hospital], name: str | None = None) -> Doctor:
    doctor = Doctor(full_name=name or _unique("Dr"), specialty="General Medicine")
    doctor.hospitals.extend(hospitals)
    session.add(doctor)
    session.flush()
    return doctor


def make_user(
    session: Session,
    role: UserRole = UserRole.ADMIN,
    email: str | None = None,
    doctor: Doctor | None = None,
    password: str | None = None,
) -> User:
    user = User(
        email=email or f"{_unique('user')}@demo.test",
        password_hash=hash_password(password) if password else "not-a-real-hash",
        role=role,
        doctor_id=doctor.id if doctor else None,
    )
    session.add(user)
    session.flush()
    return user


def make_appointment(
    session: Session,
    doctor: Doctor,
    hospital: Hospital,
    start_time: datetime = SLOT,
    **overrides: Any,
) -> Appointment:
    values: dict[str, Any] = {
        "patient_name": "Test Patient",
        "doctor_id": doctor.id,
        "hospital_id": hospital.id,
        "start_time": start_time,
        "appointment_type": AppointmentType.CONSULTATION,
        "status": AppointmentStatus.SCHEDULED,
    }
    values.update(overrides)
    appointment = Appointment(**values)
    session.add(appointment)
    session.flush()
    return appointment


@contextmanager
def violates(session: Session, constraint: str) -> Iterator[None]:
    """Expect an IntegrityError naming the constraint, without losing earlier test data."""
    with pytest.raises(IntegrityError) as excinfo, session.begin_nested():
        yield
    assert constraint in str(excinfo.value)
