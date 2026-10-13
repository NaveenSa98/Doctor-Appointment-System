"""Database access for appointments. All appointment SQL lives here."""

import uuid
from datetime import datetime
from typing import Any

from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session, joinedload

from app.core.errors import SlotConflictError
from app.models import Appointment, AppointmentStatus

SLOT_CONSTRAINT = "uq_appointments_doctor_slot"


def _is_slot_conflict(exc: IntegrityError) -> bool:
    diagnostics = getattr(exc.orig, "diag", None)
    name = getattr(diagnostics, "constraint_name", None) or str(exc.orig)
    return SLOT_CONSTRAINT in name


def get(
    session: Session, appointment_id: uuid.UUID, doctor_id: uuid.UUID | None = None
) -> Appointment | None:
    """Find a live (not soft-deleted) appointment, optionally limited to one doctor."""
    statement = (
        select(Appointment)
        .options(joinedload(Appointment.doctor), joinedload(Appointment.hospital))
        .where(Appointment.id == appointment_id, Appointment.deleted_at.is_(None))
    )
    if doctor_id is not None:
        statement = statement.where(Appointment.doctor_id == doctor_id)
    return session.scalars(statement).first()


def add(session: Session, appointment: Appointment) -> None:
    """Insert an appointment. The database index decides double bookings (409)."""
    try:
        with session.begin_nested():
            session.add(appointment)
    except IntegrityError as exc:
        if _is_slot_conflict(exc):
            raise SlotConflictError from exc
        raise


def update(session: Session, appointment: Appointment, changes: dict[str, Any]) -> None:
    """Apply field changes. The database index decides double bookings (409)."""
    try:
        with session.begin_nested():
            for field, value in changes.items():
                setattr(appointment, field, value)
    except IntegrityError as exc:
        if _is_slot_conflict(exc):
            raise SlotConflictError from exc
        raise


def soft_delete(appointment: Appointment, now: datetime) -> None:
    """Mark an appointment deleted. The row stays in the table."""
    appointment.deleted_at = now


def taken_slots(
    session: Session, doctor_id: uuid.UUID, start: datetime, end: datetime
) -> list[datetime]:
    """Start times in [start, end) that block the doctor (not cancelled, not deleted)."""
    statement = (
        select(Appointment.start_time)
        .where(
            Appointment.doctor_id == doctor_id,
            Appointment.start_time >= start,
            Appointment.start_time < end,
            Appointment.deleted_at.is_(None),
            Appointment.status != AppointmentStatus.CANCELLED,
        )
        .order_by(Appointment.start_time)
    )
    return list(session.scalars(statement))
