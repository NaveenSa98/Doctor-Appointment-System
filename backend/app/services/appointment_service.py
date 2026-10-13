"""Booking rules for appointments: who may do what, and which times are bookable."""

import math
import uuid
from datetime import datetime, timedelta

from sqlalchemy.orm import Session

from app.core.errors import ForbiddenError, NotFoundError, ValidationFailed
from app.models import Appointment, AppointmentStatus, Doctor, User, UserRole
from app.repositories import appointment_repository, doctor_repository
from app.repositories.appointment_repository import AppointmentFilters
from app.schemas.appointment import (
    AppointmentCreate,
    AppointmentListQuery,
    AppointmentOut,
    AppointmentUpdate,
)
from app.schemas.common import Page

MAX_BOOKING_HORIZON = timedelta(days=730)


def check_bookable_time(start_time: datetime, now: datetime) -> None:
    """The start must be in the future and at most two years ahead."""
    if start_time <= now:
        raise ValidationFailed("start_time", "must be in the future")
    if start_time > now + MAX_BOOKING_HORIZON:
        raise ValidationFailed("start_time", "must be within the next 2 years")


def _own_doctor_id(user: User | None) -> uuid.UUID | None:
    """The doctor a signed-in doctor is limited to, or None (admins and anonymous visitors)."""
    return user.doctor_id if user is not None and user.role == UserRole.DOCTOR else None


def _require_active_doctor(session: Session, doctor_id: uuid.UUID) -> Doctor:
    doctor = doctor_repository.get_active(session, doctor_id)
    if doctor is None:
        raise NotFoundError("Doctor not found")
    return doctor


def _require_visits(session: Session, doctor_id: uuid.UUID, hospital_id: uuid.UUID) -> None:
    if not doctor_repository.visits_hospital(session, doctor_id, hospital_id):
        raise ValidationFailed("hospital_id", "This doctor does not visit that hospital")


def _resolve_doctor_id(user: User | None, requested: uuid.UUID | None) -> uuid.UUID:
    own = _own_doctor_id(user)
    if own is not None:
        if requested is not None and requested != own:
            raise ForbiddenError("You can only book appointments for yourself")
        return own
    if requested is None:
        raise ValidationFailed("doctor_id", "doctor_id is required")
    return requested


def _get_visible(session: Session, user: User, appointment_id: uuid.UUID) -> Appointment:
    """A live appointment the user may see; doctors only see their own (404 otherwise)."""
    appointment = appointment_repository.get(session, appointment_id, _own_doctor_id(user))
    if appointment is None:
        raise NotFoundError("Appointment not found")
    return appointment


def create_appointment(
    session: Session, user: User | None, data: AppointmentCreate, now: datetime
) -> Appointment:
    """Book an appointment. Anonymous visitors may book but cannot choose a status."""
    if user is None and data.status not in (None, AppointmentStatus.SCHEDULED):
        raise ValidationFailed("status", "Only signed-in staff can set a status")
    doctor = _require_active_doctor(session, _resolve_doctor_id(user, data.doctor_id))
    _require_visits(session, doctor.id, data.hospital_id)
    check_bookable_time(data.start_time, now)

    appointment = Appointment(
        patient_name=data.patient_name,
        doctor_id=doctor.id,
        hospital_id=data.hospital_id,
        start_time=data.start_time,
        appointment_type=data.appointment_type,
        status=data.status or AppointmentStatus.SCHEDULED,
        created_by=user.id if user is not None else None,
    )
    appointment_repository.add(session, appointment)
    session.commit()
    return _get_visible_by_id(session, appointment.id)


def _get_visible_by_id(session: Session, appointment_id: uuid.UUID) -> Appointment:
    appointment = appointment_repository.get(session, appointment_id)
    if appointment is None:  # pragma: no cover - the row was just written
        raise NotFoundError("Appointment not found")
    return appointment


def list_appointments(
    session: Session, user: User, query: AppointmentListQuery
) -> Page[AppointmentOut]:
    """Search, filter, sort and paginate. Doctors are always limited to their own."""
    if query.date_from and query.date_to and query.date_from > query.date_to:
        raise ValidationFailed("date_to", "must not be before date_from")
    filters = AppointmentFilters(
        q=query.q,
        doctor_id=_own_doctor_id(user) or query.doctor_id,
        hospital_id=query.hospital_id,
        statuses=query.status,
        types=query.type,
        date_from=query.date_from,
        date_to=query.date_to,
    )
    offset = (query.page - 1) * query.page_size
    items, total = appointment_repository.search(
        session, filters, query.sort, offset, query.page_size
    )
    return Page[AppointmentOut](
        items=[AppointmentOut.model_validate(item) for item in items],
        total=total,
        page=query.page,
        page_size=query.page_size,
        pages=math.ceil(total / query.page_size),
    )


def get_appointment(session: Session, user: User, appointment_id: uuid.UUID) -> Appointment:
    """Return one appointment the user may see."""
    return _get_visible(session, user, appointment_id)


def update_appointment(
    session: Session,
    user: User,
    appointment_id: uuid.UUID,
    data: AppointmentUpdate,
    now: datetime,
) -> Appointment:
    """Change an appointment. The time rule only applies when the time or doctor changes."""
    appointment = _get_visible(session, user, appointment_id)
    changes = data.model_dump(exclude_unset=True)
    doctor_id = changes.get("doctor_id", appointment.doctor_id)
    hospital_id = changes.get("hospital_id", appointment.hospital_id)
    start_time = changes.get("start_time", appointment.start_time)

    own = _own_doctor_id(user)
    if own is not None and doctor_id != own:
        raise ForbiddenError("You can only manage your own appointments")
    doctor_changed = doctor_id != appointment.doctor_id
    if doctor_changed:
        _require_active_doctor(session, doctor_id)
    if doctor_changed or hospital_id != appointment.hospital_id:
        _require_visits(session, doctor_id, hospital_id)
    if doctor_changed or start_time != appointment.start_time:
        check_bookable_time(start_time, now)

    appointment_repository.update(session, appointment, changes)
    session.commit()
    return _get_visible_by_id(session, appointment_id)


def delete_appointment(
    session: Session, user: User, appointment_id: uuid.UUID, now: datetime
) -> None:
    """Soft-delete an appointment the user may see."""
    appointment = _get_visible(session, user, appointment_id)
    appointment_repository.soft_delete(appointment, now)
    session.commit()
