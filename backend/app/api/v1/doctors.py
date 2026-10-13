"""Public doctor endpoints."""

import uuid
from datetime import datetime

from fastapi import APIRouter

from app.api.v1.deps import SessionDep
from app.models import Doctor
from app.schemas.doctor import AvailabilityOut, DoctorOut
from app.services import doctor_service

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
