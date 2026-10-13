"""Database access for appointments. All appointment SQL lives here."""

import uuid
from collections.abc import Sequence
from dataclasses import dataclass
from datetime import datetime
from typing import Any

from sqlalchemy import ColumnElement, func, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session, joinedload

from app.core.errors import SlotConflictError
from app.models import Appointment, AppointmentSort, AppointmentStatus, AppointmentType

SLOT_CONSTRAINT = "uq_appointments_doctor_slot"

# (sort expression, descending?). The expression is a column or a SQL function.
_SORT_COLUMNS: dict[AppointmentSort, tuple[Any, bool]] = {
    AppointmentSort.START_TIME: (Appointment.start_time, False),
    AppointmentSort.START_TIME_DESC: (Appointment.start_time, True),
    AppointmentSort.PATIENT_NAME: (func.lower(Appointment.patient_name), False),
    AppointmentSort.PATIENT_NAME_DESC: (func.lower(Appointment.patient_name), True),
    AppointmentSort.CREATED_AT: (Appointment.created_at, False),
    AppointmentSort.CREATED_AT_DESC: (Appointment.created_at, True),
}


@dataclass(frozen=True)
class AppointmentFilters:
    """Optional filters for listing appointments. Empty values mean "no filter"."""

    q: str | None = None
    doctor_id: uuid.UUID | None = None
    hospital_id: uuid.UUID | None = None
    statuses: Sequence[AppointmentStatus] = ()
    types: Sequence[AppointmentType] = ()
    date_from: datetime | None = None
    date_to: datetime | None = None


def escape_like(value: str) -> str:
    """Escape LIKE wildcards so user input is matched literally."""
    return value.replace("\\", "\\\\").replace("%", "\\%").replace("_", "\\_")


def _conditions(filters: AppointmentFilters) -> list[ColumnElement[bool]]:
    conditions: list[ColumnElement[bool]] = [Appointment.deleted_at.is_(None)]
    if filters.q:
        pattern = f"%{escape_like(filters.q)}%"
        conditions.append(Appointment.patient_name.ilike(pattern, escape="\\"))
    if filters.doctor_id is not None:
        conditions.append(Appointment.doctor_id == filters.doctor_id)
    if filters.hospital_id is not None:
        conditions.append(Appointment.hospital_id == filters.hospital_id)
    if filters.statuses:
        conditions.append(Appointment.status.in_(filters.statuses))
    if filters.types:
        conditions.append(Appointment.appointment_type.in_(filters.types))
    if filters.date_from is not None:
        conditions.append(Appointment.start_time >= filters.date_from)
    if filters.date_to is not None:
        conditions.append(Appointment.start_time < filters.date_to)
    return conditions


def search(
    session: Session, filters: AppointmentFilters, sort: AppointmentSort, offset: int, limit: int
) -> tuple[list[Appointment], int]:
    """One page of matching live appointments plus the total number of matches.

    The id is a final tie-break, so pages stay stable when the sort column has duplicates.
    """
    conditions = _conditions(filters)
    total = session.scalar(select(func.count()).select_from(Appointment).where(*conditions)) or 0
    column, descending = _SORT_COLUMNS[sort]
    statement = (
        select(Appointment)
        .options(joinedload(Appointment.doctor), joinedload(Appointment.hospital))
        .where(*conditions)
        .order_by(column.desc() if descending else column.asc(), Appointment.id.asc())
        .offset(offset)
        .limit(limit)
    )
    return list(session.scalars(statement)), total


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
