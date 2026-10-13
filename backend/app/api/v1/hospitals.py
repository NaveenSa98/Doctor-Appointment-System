"""Public hospital endpoint."""

import uuid

from fastapi import APIRouter

from app.api.v1.deps import SessionDep
from app.models import Hospital
from app.schemas.hospital import HospitalOut
from app.services import hospital_service

router = APIRouter(prefix="/hospitals", tags=["hospitals"])


@router.get("", response_model=list[HospitalOut])
def list_hospitals(session: SessionDep, doctor_id: uuid.UUID | None = None) -> list[Hospital]:
    """All hospitals, or only those a given doctor visits."""
    return hospital_service.list_hospitals(session, doctor_id)
