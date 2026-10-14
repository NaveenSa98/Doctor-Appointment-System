"""Staff view of registered patients. Doctors only see patients who booked with them."""

import math
import uuid

from sqlalchemy.orm import Session

from app.core.errors import ForbiddenError, NotFoundError
from app.models import AppointmentSort, User, UserRole
from app.repositories import appointment_repository, patient_repository
from app.repositories.appointment_repository import AppointmentFilters
from app.repositories.patient_repository import PatientRow
from app.schemas.appointment import AppointmentOut
from app.schemas.common import Page
from app.schemas.patient import PatientDetail, PatientListQuery, PatientOut

MAX_BOOKINGS = 100


def _scope(user: User) -> uuid.UUID | None:
    """The doctor a doctor-user is limited to; None for an admin. Patients get a 403."""
    if user.role == UserRole.PATIENT:
        raise ForbiddenError("Patient details are only available to staff")
    return user.doctor_id if user.role == UserRole.DOCTOR else None


def _out(row: PatientRow) -> PatientOut:
    return PatientOut(
        id=row.user.id,
        full_name=row.user.full_name,
        email=row.user.email,
        is_active=row.user.is_active,
        created_at=row.user.created_at,
        booking_count=row.booking_count,
        last_booking_at=row.last_booking_at,
    )


def list_patients(session: Session, user: User, query: PatientListQuery) -> Page[PatientOut]:
    """Search registered patients by name or email."""
    offset = (query.page - 1) * query.page_size
    rows, total = patient_repository.search(session, query.q, _scope(user), offset, query.page_size)
    return Page[PatientOut](
        items=[_out(row) for row in rows],
        total=total,
        page=query.page,
        page_size=query.page_size,
        pages=math.ceil(total / query.page_size),
    )


def get_patient(session: Session, user: User, patient_id: uuid.UUID) -> PatientDetail:
    """A patient and their bookings (a doctor sees only the bookings with themself)."""
    doctor_id = _scope(user)
    row = patient_repository.get(session, patient_id, doctor_id)
    if row is None:
        raise NotFoundError("Patient not found")
    filters = AppointmentFilters(created_by=patient_id, doctor_id=doctor_id)
    bookings, _total = appointment_repository.search(
        session, filters, AppointmentSort.START_TIME_DESC, 0, MAX_BOOKINGS
    )
    return PatientDetail(
        **_out(row).model_dump(),
        bookings=[AppointmentOut.model_validate(booking) for booking in bookings],
    )
