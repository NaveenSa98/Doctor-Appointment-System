"""Doctor lookups and availability."""

import uuid
from datetime import datetime, timedelta

from sqlalchemy.orm import Session

from app.core.errors import NotFoundError, ValidationFailed
from app.models import Doctor
from app.repositories import appointment_repository, doctor_repository
from app.schemas.doctor import AvailabilityOut

MAX_AVAILABILITY_WINDOW = timedelta(days=7)


def list_doctors(session: Session, hospital_id: uuid.UUID | None) -> list[Doctor]:
    """Active doctors, optionally only those visiting a hospital."""
    return doctor_repository.list_active(session, hospital_id)


def require_aware(field: str, value: datetime) -> None:
    if value.tzinfo is None or value.utcoffset() is None:
        raise ValidationFailed(field, "must include a timezone, for example 2030-01-15T00:00:00Z")


def availability(
    session: Session, doctor_id: uuid.UUID, date_from: datetime, date_to: datetime
) -> AvailabilityOut:
    """Start times already taken for a doctor in [date_from, date_to). No patient data."""
    require_aware("date_from", date_from)
    require_aware("date_to", date_to)
    if date_to <= date_from:
        raise ValidationFailed("date_to", "must be after date_from")
    if date_to - date_from > MAX_AVAILABILITY_WINDOW:
        raise ValidationFailed("date_to", "the window may be at most 7 days")
    if doctor_repository.get_active(session, doctor_id) is None:
        raise NotFoundError("Doctor not found")
    taken = appointment_repository.taken_slots(session, doctor_id, date_from, date_to)
    return AvailabilityOut(doctor_id=doctor_id, taken=taken)
