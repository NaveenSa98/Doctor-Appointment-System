"""Database access for hospitals."""

import uuid

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.models import Hospital, doctor_hospitals


def list_all(session: Session, doctor_id: uuid.UUID | None = None) -> list[Hospital]:
    """Hospitals by name, optionally only those a given doctor visits."""
    statement = select(Hospital).order_by(func.lower(Hospital.name))
    if doctor_id is not None:
        visited = select(doctor_hospitals.c.hospital_id).where(
            doctor_hospitals.c.doctor_id == doctor_id
        )
        statement = statement.where(Hospital.id.in_(visited))
    return list(session.scalars(statement))
