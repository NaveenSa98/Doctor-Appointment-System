"""Public doctor endpoints."""

import uuid
from datetime import datetime

from fastapi import APIRouter

from app.api.v1.deps import CurrentUser, SessionDep, SettingsDep
from app.core.errors import ForbiddenError
from app.models import Doctor, UserRole
from app.schemas.doctor import AvailabilityOut, DoctorOut
from app.schemas.schedule import SessionsOut, SlotsOut
from app.services import doctor_service, schedule_service

router = APIRouter(prefix="/doctors", tags=["doctors"])


@router.get("", response_model=list[DoctorOut])
def list_doctors(session: SessionDep, hospital_id: uuid.UUID | None = None) -> list[Doctor]:
    """Active doctors, optionally only those visiting one hospital."""
    return doctor_service.list_doctors(session, hospital_id)


@router.get("/{doctor_id}/availability", response_model=AvailabilityOut)
def doctor_availability(
    doctor_id: uuid.UUID, session: SessionDep, date_from: datetime, date_to: datetime
) -> AvailabilityOut:
    """Start times already taken in [date_from, date_to), at most 7 days."""
    return doctor_service.availability(session, doctor_id, date_from, date_to)


@router.get("/{doctor_id}/slots", response_model=SlotsOut)
def doctor_slots(
    doctor_id: uuid.UUID,
    session: SessionDep,
    settings: SettingsDep,
    hospital_id: uuid.UUID,
    date_from: datetime,
    date_to: datetime,
) -> SlotsOut:
    """Bookable start times at one hospital in [date_from, date_to), at most 7 days."""
    return schedule_service.doctor_slots(
        session, doctor_id, hospital_id, date_from, date_to, settings.clinic_utc_offset_minutes
    )


@router.get("/{doctor_id}/sessions", response_model=SessionsOut)
def doctor_sessions(
    doctor_id: uuid.UUID, session: SessionDep, settings: SettingsDep, user: CurrentUser
) -> SessionsOut:
    """A doctor's weekly schedule. Admins can read any; a doctor can read their own."""
    if user.role != UserRole.ADMIN and user.doctor_id != doctor_id:
        raise ForbiddenError("You can only view your own schedule")
    return schedule_service.list_sessions(session, doctor_id, settings.clinic_utc_offset_minutes)
