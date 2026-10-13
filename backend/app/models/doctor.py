"""Doctor model and the doctor-hospital link table."""

import uuid
from datetime import datetime
from typing import TYPE_CHECKING

from sqlalchemy import Column, ForeignKey, Index, Table, Text, func, text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base

if TYPE_CHECKING:
    from app.models.hospital import Hospital

doctor_hospitals = Table(
    "doctor_hospitals",
    Base.metadata,
    Column("doctor_id", ForeignKey("doctors.id", ondelete="RESTRICT"), primary_key=True),
    Column("hospital_id", ForeignKey("hospitals.id", ondelete="RESTRICT"), primary_key=True),
    Index("ix_doctor_hospitals_hospital", "hospital_id", "doctor_id"),
)


class Doctor(Base):
    """A doctor who can visit several hospitals."""

    __tablename__ = "doctors"

    id: Mapped[uuid.UUID] = mapped_column(
        primary_key=True, default=uuid.uuid4, server_default=text("gen_random_uuid()")
    )
    full_name: Mapped[str] = mapped_column(Text)
    specialty: Mapped[str] = mapped_column(Text)
    is_active: Mapped[bool] = mapped_column(default=True, server_default=text("true"))
    created_at: Mapped[datetime] = mapped_column(server_default=func.now())

    hospitals: Mapped[list["Hospital"]] = relationship(
        secondary=doctor_hospitals, back_populates="doctors"
    )
