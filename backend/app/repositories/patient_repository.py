"""Database access for registered patients (users with the patient role)."""

import uuid
from dataclasses import dataclass
from datetime import datetime
from typing import Any

from sqlalchemy import ColumnElement, Select, Subquery, func, select
from sqlalchemy.orm import Session

from app.models import Appointment, User, UserRole
from app.repositories.appointment_repository import escape_like


@dataclass(frozen=True)
class PatientRow:
    """A patient with how many live bookings they made, and when the latest one starts."""

    user: User
    booking_count: int
    last_booking_at: datetime | None


def _bookings(doctor_id: uuid.UUID | None) -> Subquery:
    """Per-patient booking totals, optionally only with one doctor (soft-deleted rows ignored)."""
    conditions: list[ColumnElement[bool]] = [
        Appointment.deleted_at.is_(None),
        Appointment.created_by.is_not(None),
    ]
    if doctor_id is not None:
        conditions.append(Appointment.doctor_id == doctor_id)
    return (
        select(
            Appointment.created_by.label("patient_id"),
            func.count().label("total"),
            func.max(Appointment.start_time).label("last_start"),
        )
        .where(*conditions)
        .group_by(Appointment.created_by)
        .subquery()
    )


def _query(q: str | None, doctor_id: uuid.UUID | None) -> Select[Any]:
    totals = _bookings(doctor_id)
    statement = (
        select(User, func.coalesce(totals.c.total, 0), totals.c.last_start)
        .outerjoin(totals, totals.c.patient_id == User.id)
        .where(User.role == UserRole.PATIENT)
    )
    if doctor_id is not None:  # a doctor only sees patients who booked with them
        statement = statement.where(totals.c.total.is_not(None))
    if q:
        pattern = f"%{escape_like(q)}%"
        statement = statement.where(
            User.full_name.ilike(pattern, escape="\\") | User.email.ilike(pattern, escape="\\")
        )
    return statement


def search(
    session: Session, q: str | None, doctor_id: uuid.UUID | None, offset: int, limit: int
) -> tuple[list[PatientRow], int]:
    """One page of patients (by name, then id) plus the total number of matches."""
    statement = _query(q, doctor_id)
    total = session.scalar(select(func.count()).select_from(statement.subquery())) or 0
    page = statement.order_by(func.lower(func.coalesce(User.full_name, User.email)), User.id)
    rows = session.execute(page.offset(offset).limit(limit))
    return [PatientRow(user, count, last) for user, count, last in rows], total


def get(session: Session, patient_id: uuid.UUID, doctor_id: uuid.UUID | None) -> PatientRow | None:
    """One patient, or None (unknown, not a patient, or, for a doctor, never booked with them)."""
    statement = _query(None, doctor_id).where(User.id == patient_id)
    row = session.execute(statement).first()
    return PatientRow(row[0], row[1], row[2]) if row else None
