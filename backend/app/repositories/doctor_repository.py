"""Database access for doctors."""

import uuid

from sqlalchemy import exists, select
from sqlalchemy.orm import Session, selectinload

from app.models import Doctor, doctor_hospitals


def get_active(session: Session, doctor_id: uuid.UUID) -> Doctor | None:
    """Find an active doctor."""
    return session.scalar(select(Doctor).where(Doctor.id == doctor_id, Doctor.is_active.is_(True)))


def list_active(session: Session, hospital_id: uuid.UUID | None = None) -> list[Doctor]:
    """Active doctors with their hospitals, optionally only those visiting one hospital."""
    statement = (
        select(Doctor)
        .options(selectinload(Doctor.hospitals))
        .where(Doctor.is_active.is_(True))
        .order_by(Doctor.full_name)
    )
    if hospital_id is not None:
        visiting = select(doctor_hospitals.c.doctor_id).where(
            doctor_hospitals.c.hospital_id == hospital_id
        )
        statement = statement.where(Doctor.id.in_(visiting))
    return list(session.scalars(statement))


def visits_hospital(session: Session, doctor_id: uuid.UUID, hospital_id: uuid.UUID) -> bool:
    """True if the doctor is linked to the hospital."""
    link = exists().where(
        doctor_hospitals.c.doctor_id == doctor_id,
        doctor_hospitals.c.hospital_id == hospital_id,
    )
    return bool(session.scalar(select(link)))
