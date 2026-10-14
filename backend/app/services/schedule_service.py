"""Weekly doctor sessions: who may book when, and the admin's changes to the schedule."""

import uuid
from collections.abc import Callable
from datetime import date, datetime

from sqlalchemy.orm import Session

from app.core.errors import AppError, NotFoundError, ValidationFailed
from app.models import DoctorSession, SessionExclusion
from app.repositories import appointment_repository, doctor_repository, session_repository
from app.schemas.hospital import HospitalOut
from app.schemas.schedule import (
    SessionCreate,
    SessionOut,
    SessionsOut,
    SessionUpdate,
    SkipDateCreate,
    SkippedDateOut,
    SlotsOut,
)
from app.services import schedule
from app.services.doctor_service import MAX_AVAILABILITY_WINDOW, require_aware
from app.services.schedule import SessionRule


def _rule(item: DoctorSession) -> SessionRule:
    return SessionRule(
        hospital_id=item.hospital_id,
        weekday=item.weekday,
        start=item.start_time,
        end=item.end_time,
        skipped=frozenset(x.on_date for x in item.exclusions),
    )


def _rules(session: Session, doctor_id: uuid.UUID) -> list[SessionRule]:
    return [_rule(item) for item in session_repository.list_for_doctor(session, doctor_id)]


# ---- used when booking ------------------------------------------------------------------------


def require_slot_allowed(
    session: Session,
    doctor_id: uuid.UUID,
    hospital_id: uuid.UUID,
    start: datetime,
    offset_minutes: int,
) -> None:
    """A doctor with sessions can only be booked inside them. No sessions: no restriction."""
    rules = _rules(session, doctor_id)
    if rules and not schedule.slot_allowed(rules, hospital_id, start, offset_minutes):
        raise ValidationFailed("start_time", "is outside the doctor's sessions at this hospital")


def doctor_slots(
    session: Session,
    doctor_id: uuid.UUID,
    hospital_id: uuid.UUID,
    date_from: datetime,
    date_to: datetime,
    offset_minutes: int,
) -> SlotsOut:
    """Bookable start times for one doctor and hospital in [date_from, date_to), at most 7 days."""
    require_aware("date_from", date_from)
    require_aware("date_to", date_to)
    if date_to <= date_from:
        raise ValidationFailed("date_to", "must be after date_from")
    if date_to - date_from > MAX_AVAILABILITY_WINDOW:
        raise ValidationFailed("date_to", "the window may be at most 7 days")
    if doctor_repository.get_active(session, doctor_id) is None:
        raise NotFoundError("Doctor not found")
    rules = _rules(session, doctor_id)
    slots = schedule.generate_slots(rules, hospital_id, date_from, date_to, offset_minutes)
    return SlotsOut(
        doctor_id=doctor_id, hospital_id=hospital_id, restricted=bool(rules), slots=slots
    )


# ---- reading and changing the schedule --------------------------------------------------------


def _out(item: DoctorSession) -> SessionOut:
    return SessionOut(
        id=item.id,
        hospital=HospitalOut.model_validate(item.hospital),
        weekday=item.weekday,
        start_time=item.start_time,
        end_time=item.end_time,
        skipped=[SkippedDateOut.model_validate(x) for x in item.exclusions],
    )


def list_sessions(session: Session, doctor_id: uuid.UUID, offset_minutes: int) -> SessionsOut:
    """A doctor's weekly schedule (any status of doctor)."""
    if doctor_repository.get(session, doctor_id) is None:
        raise NotFoundError("Doctor not found")
    items = session_repository.list_for_doctor(session, doctor_id)
    return SessionsOut(
        doctor_id=doctor_id,
        utc_offset_minutes=offset_minutes,
        sessions=[_out(item) for item in items],
    )


def _require_session(session: Session, session_id: uuid.UUID) -> DoctorSession:
    item = session_repository.get(session, session_id)
    if item is None:
        raise NotFoundError("Session not found")
    return item


def _check_no_overlap(
    session: Session, doctor_id: uuid.UUID, candidate: DoctorSession, ignore: uuid.UUID | None
) -> None:
    for other in session_repository.list_for_doctor(session, doctor_id):
        if other.id == ignore or other.weekday != candidate.weekday:
            continue
        if schedule.overlaps(
            candidate.start_time, candidate.end_time, other.start_time, other.end_time
        ):
            raise AppError(
                409,
                "session_overlap",
                "This doctor already has a session that overlaps this time on that day",
            )


def _check_not_leaving_bookings(
    session: Session,
    item: DoctorSession,
    now: datetime,
    offset_minutes: int,
    still_covered: Callable[[datetime], bool],
) -> None:
    """Refuse a change that would strand an upcoming booking outside every session."""
    current = _rule(item)
    starts = appointment_repository.upcoming_starts(session, item.doctor_id, item.hospital_id, now)
    for start in starts:
        local = schedule.to_clinic(start, offset_minutes)
        if schedule.covers(current, item.hospital_id, local) and not still_covered(local):
            raise AppError(
                409,
                "session_has_appointments",
                "There are upcoming appointments in this session. Cancel or move them first.",
            )


def _check_visits(session: Session, doctor_id: uuid.UUID, hospital_id: uuid.UUID) -> None:
    doctor = doctor_repository.get(session, doctor_id)
    if doctor is None:
        raise NotFoundError("Doctor not found")
    if hospital_id not in {hospital.id for hospital in doctor.hospitals}:
        raise ValidationFailed("hospital_id", "this doctor does not visit that hospital")


def create_session(session: Session, doctor_id: uuid.UUID, data: SessionCreate) -> SessionOut:
    """Add a weekly session at one of the doctor's hospitals."""
    _check_visits(session, doctor_id, data.hospital_id)
    item = DoctorSession(
        doctor_id=doctor_id,
        hospital_id=data.hospital_id,
        weekday=data.weekday,
        start_time=data.start_time,
        end_time=data.end_time,
    )
    _check_no_overlap(session, doctor_id, item, ignore=None)
    session_repository.add(session, item)
    session.commit()
    return _out(_require_session(session, item.id))


def update_session(
    session: Session,
    session_id: uuid.UUID,
    data: SessionUpdate,
    now: datetime,
    offset_minutes: int,
) -> SessionOut:
    """Change a session's hospital, weekday or hours."""
    item = _require_session(session, session_id)
    changes = data.model_dump(exclude_unset=True)
    hospital_id = changes.get("hospital_id", item.hospital_id)
    weekday = changes.get("weekday", item.weekday)
    start = changes.get("start_time", item.start_time)
    end = changes.get("end_time", item.end_time)
    if end <= start:
        raise ValidationFailed("end_time", "must be after start_time")
    _check_visits(session, item.doctor_id, hospital_id)

    candidate = DoctorSession(
        doctor_id=item.doctor_id,
        hospital_id=hospital_id,
        weekday=weekday,
        start_time=start,
        end_time=end,
    )
    _check_no_overlap(session, item.doctor_id, candidate, ignore=item.id)
    new_rule = SessionRule(hospital_id, weekday, start, end)
    _check_not_leaving_bookings(
        session,
        item,
        now,
        offset_minutes,
        lambda local: schedule.covers(new_rule, hospital_id, local),
    )

    if hospital_id != item.hospital_id or weekday != item.weekday:
        item.exclusions.clear()  # skipped dates belong to the old weekday
    item.hospital_id, item.weekday, item.start_time, item.end_time = (
        hospital_id,
        weekday,
        start,
        end,
    )
    session.commit()
    session.expire_all()
    return _out(_require_session(session, session_id))


def delete_session(
    session: Session, session_id: uuid.UUID, now: datetime, offset_minutes: int
) -> None:
    """Remove a weekly session. Without any session left, the doctor is unrestricted again."""
    item = _require_session(session, session_id)
    _check_not_leaving_bookings(session, item, now, offset_minutes, lambda _local: False)
    session_repository.delete(session, item)
    session.commit()


def skip_date(
    session: Session,
    session_id: uuid.UUID,
    data: SkipDateCreate,
    now: datetime,
    offset_minutes: int,
) -> SessionOut:
    """Take one day out of a weekly session (leave, a holiday)."""
    item = _require_session(session, session_id)
    if data.date < schedule.to_clinic(now, offset_minutes).date():
        raise ValidationFailed("date", "must not be in the past")
    if data.date.weekday() != item.weekday:
        raise ValidationFailed("date", "this session does not run on that weekday")
    if session_repository.find_exclusion(session, item.id, data.date) is not None:
        raise AppError(409, "already_skipped", "That day is already skipped")

    _check_not_leaving_bookings(
        session, item, now, offset_minutes, lambda local: local.date() != data.date
    )
    item.exclusions.append(SessionExclusion(on_date=data.date, reason=data.reason))
    session.commit()
    session.expire_all()
    return _out(_require_session(session, session_id))


def restore_date(session: Session, session_id: uuid.UUID, day: date) -> SessionOut:
    """Put a skipped day back."""
    item = _require_session(session, session_id)
    exclusion = session_repository.find_exclusion(session, item.id, day)
    if exclusion is None:
        raise NotFoundError("That day is not skipped")
    item.exclusions.remove(exclusion)
    session.commit()
    session.expire_all()
    return _out(_require_session(session, session_id))
