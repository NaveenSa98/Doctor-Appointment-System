"""Weekly sessions: when a doctor sees patients at a hospital, plus single days taken out."""

import uuid
from datetime import date, datetime, time

from sqlalchemy import CheckConstraint, ForeignKey, Index, Text, UniqueConstraint, func, text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base
from app.models.hospital import Hospital


class DoctorSession(Base):
    """A recurring weekly session in clinic time, e.g. Mondays 09:00-13:00 at one hospital.

    `weekday` follows Python: Monday is 0 and Sunday is 6. Times are wall-clock times at the
    clinic (see Settings.clinic_utc_offset_minutes); bookable slots start every 30 minutes
    from `start_time` up to, but not including, `end_time`.
    """

    __tablename__ = "doctor_sessions"
    __table_args__ = (
        CheckConstraint("weekday BETWEEN 0 AND 6", name="weekday_range"),
        CheckConstraint("end_time > start_time", name="ends_after_start"),
        CheckConstraint(
            "date_part('minute', start_time) IN (0, 30)"
            " AND date_part('minute', end_time) IN (0, 30)"
            " AND date_part('second', start_time) = 0 AND date_part('second', end_time) = 0",
            name="half_hour_aligned",
        ),
        Index("ix_doctor_sessions_doctor_weekday", "doctor_id", "weekday"),
    )

    id: Mapped[uuid.UUID] = mapped_column(
        primary_key=True, default=uuid.uuid4, server_default=text("gen_random_uuid()")
    )
    doctor_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("doctors.id", ondelete="CASCADE"))
    hospital_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("hospitals.id", ondelete="RESTRICT"))
    weekday: Mapped[int]
    start_time: Mapped[time]
    end_time: Mapped[time]
    created_at: Mapped[datetime] = mapped_column(server_default=func.now())

    hospital: Mapped[Hospital] = relationship()
    exclusions: Mapped[list["SessionExclusion"]] = relationship(
        cascade="all, delete-orphan", passive_deletes=True, order_by="SessionExclusion.on_date"
    )


class SessionExclusion(Base):
    """One clinic-local date on which a weekly session does not run (leave, a holiday)."""

    __tablename__ = "session_exclusions"
    __table_args__ = (UniqueConstraint("session_id", "on_date", name="uq_session_exclusions_day"),)

    id: Mapped[uuid.UUID] = mapped_column(
        primary_key=True, default=uuid.uuid4, server_default=text("gen_random_uuid()")
    )
    session_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("doctor_sessions.id", ondelete="CASCADE")
    )
    on_date: Mapped[date]
    reason: Mapped[str | None] = mapped_column(Text)
    created_at: Mapped[datetime] = mapped_column(server_default=func.now())
