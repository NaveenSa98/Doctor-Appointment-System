"""Appointment model.

The trigram index on patient_name is created only in the migration, because its operator
class lives in whichever schema holds the pg_trgm extension.
"""

import uuid
from datetime import datetime

from sqlalchemy import (
    CheckConstraint,
    Enum,
    ForeignKey,
    ForeignKeyConstraint,
    Index,
    String,
    func,
    text,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base
from app.models.doctor import Doctor
from app.models.enums import AppointmentStatus, AppointmentType, enum_values
from app.models.hospital import Hospital

_ACTIVE_SLOT = "status <> 'cancelled' AND deleted_at IS NULL"
_NOT_DELETED = "deleted_at IS NULL"


class Appointment(Base):
    """A booking of a doctor at a hospital. Deleted rows are soft-deleted via deleted_at."""

    __tablename__ = "appointments"
    __table_args__ = (
        ForeignKeyConstraint(
            ["doctor_id", "hospital_id"],
            ["doctor_hospitals.doctor_id", "doctor_hospitals.hospital_id"],
            name="fk_appointments_doctor_hospital",
            ondelete="RESTRICT",
        ),
        CheckConstraint("char_length(btrim(patient_name)) >= 2", name="patient_name_length"),
        CheckConstraint(
            "date_part('minute', start_time AT TIME ZONE 'UTC') IN (0, 30) "
            "AND date_part('second', start_time AT TIME ZONE 'UTC') = 0",
            name="slot_aligned",
        ),
        # One active appointment per doctor and start time, whatever the hospital.
        Index(
            "uq_appointments_doctor_slot",
            "doctor_id",
            "start_time",
            unique=True,
            postgresql_where=text(_ACTIVE_SLOT),
        ),
        Index("ix_appointments_start_time", "start_time", postgresql_where=text(_NOT_DELETED)),
        Index(
            "ix_appointments_doctor_start",
            "doctor_id",
            "start_time",
            postgresql_where=text(_NOT_DELETED),
        ),
        Index(
            "ix_appointments_status_start",
            "status",
            "start_time",
            postgresql_where=text(_NOT_DELETED),
        ),
        Index(
            "ix_appointments_hospital_start",
            "hospital_id",
            "start_time",
            postgresql_where=text(_NOT_DELETED),
        ),
    )

    id: Mapped[uuid.UUID] = mapped_column(
        primary_key=True, default=uuid.uuid4, server_default=text("gen_random_uuid()")
    )
    patient_name: Mapped[str] = mapped_column(String(100))
    doctor_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("doctors.id", ondelete="RESTRICT"))
    hospital_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("hospitals.id", ondelete="RESTRICT"))
    start_time: Mapped[datetime]
    appointment_type: Mapped[AppointmentType] = mapped_column(
        Enum(AppointmentType, name="appointment_type", values_callable=enum_values)
    )
    status: Mapped[AppointmentStatus] = mapped_column(
        Enum(AppointmentStatus, name="appointment_status", values_callable=enum_values),
        default=AppointmentStatus.SCHEDULED,
        server_default=text("'scheduled'"),
    )
    created_by: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("users.id", ondelete="SET NULL")
    )
    created_at: Mapped[datetime] = mapped_column(server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(server_default=func.now(), onupdate=func.now())
    deleted_at: Mapped[datetime | None]

    doctor: Mapped[Doctor] = relationship()
    hospital: Mapped[Hospital] = relationship()
