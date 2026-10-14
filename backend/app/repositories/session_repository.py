"""Database access for weekly doctor sessions and their skipped days."""

import uuid
from collections.abc import Sequence
from datetime import date

from sqlalchemy import select
from sqlalchemy.orm import Session, selectinload

from app.models import DoctorSession, SessionExclusion


def list_for_doctor(session: Session, doctor_id: uuid.UUID) -> list[DoctorSession]:
    """A doctor's sessions with skipped days, ordered by weekday then start time."""
    statement = (
        select(DoctorSession)
        .options(selectinload(DoctorSession.exclusions), selectinload(DoctorSession.hospital))
        .where(DoctorSession.doctor_id == doctor_id)
        .order_by(DoctorSession.weekday, DoctorSession.start_time)
    )
    return list(session.scalars(statement))


def get(session: Session, session_id: uuid.UUID) -> DoctorSession | None:
    """Find one session with its skipped days."""
    return session.scalar(
        select(DoctorSession)
        .options(selectinload(DoctorSession.exclusions), selectinload(DoctorSession.hospital))
        .where(DoctorSession.id == session_id)
    )


def add(session: Session, doctor_session: DoctorSession) -> None:
    """Insert a session."""
    session.add(doctor_session)
    session.flush()


def delete(session: Session, doctor_session: DoctorSession) -> None:
    """Remove a session; its skipped days go with it."""
    session.delete(doctor_session)
    session.flush()


def find_exclusion(
    session: Session, session_id: uuid.UUID, on_date: date
) -> SessionExclusion | None:
    """The skipped-day row for a session and date, if any."""
    return session.scalar(
        select(SessionExclusion).where(
            SessionExclusion.session_id == session_id, SessionExclusion.on_date == on_date
        )
    )


def hospitals_with_sessions(
    session: Session, doctor_id: uuid.UUID, hospital_ids: Sequence[uuid.UUID]
) -> set[uuid.UUID]:
    """Which of these hospitals have at least one session for the doctor."""
    statement = select(DoctorSession.hospital_id).where(
        DoctorSession.doctor_id == doctor_id, DoctorSession.hospital_id.in_(hospital_ids)
    )
    return set(session.scalars(statement))


def count_for_doctor(session: Session, doctor_id: uuid.UUID) -> int:
    """How many sessions the doctor has (zero means "no schedule set")."""
    return len(list_for_doctor(session, doctor_id))
