"""Database access for hospitals."""

import uuid
from collections.abc import Sequence

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


def get_many(session: Session, hospital_ids: Sequence[uuid.UUID]) -> list[Hospital]:
    """The hospitals with these ids (missing ids are simply absent from the result)."""
    return list(session.scalars(select(Hospital).where(Hospital.id.in_(hospital_ids))))
