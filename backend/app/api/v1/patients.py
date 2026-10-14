"""Staff endpoints for registered patients. Patients themselves get a 403."""

import uuid
from typing import Annotated

from fastapi import APIRouter, Query

from app.api.v1.deps import CurrentUser, SessionDep
from app.schemas.common import Page
from app.schemas.patient import PatientDetail, PatientListQuery, PatientOut
from app.services import patient_service

router = APIRouter(prefix="/patients", tags=["patients"])


@router.get("", response_model=Page[PatientOut])
def list_patients(
    query: Annotated[PatientListQuery, Query()], session: SessionDep, user: CurrentUser
) -> Page[PatientOut]:
    """Registered patients. Admins see everyone; doctors see patients who booked with them."""
    return patient_service.list_patients(session, user, query)


@router.get("/{patient_id}", response_model=PatientDetail)
def get_patient(patient_id: uuid.UUID, session: SessionDep, user: CurrentUser) -> PatientDetail:
    """One patient with their bookings (a doctor sees only the bookings with themself)."""
    return patient_service.get_patient(session, user, patient_id)
