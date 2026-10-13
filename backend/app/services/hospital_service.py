"""Hospital lookups."""

import uuid

from sqlalchemy.orm import Session

from app.models import Hospital
from app.repositories import hospital_repository


def list_hospitals(session: Session, doctor_id: uuid.UUID | None) -> list[Hospital]:
    """All hospitals, or those a given doctor visits."""
    return hospital_repository.list_all(session, doctor_id)
