"""User account model (admins, doctors and patients)."""

import uuid
from datetime import datetime

from sqlalchemy import CheckConstraint, Enum, ForeignKey, Index, Text, func, text
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base
from app.models.enums import UserRole, enum_values


class User(Base):
    """An account. Doctor accounts are linked to a doctor profile."""

    __tablename__ = "users"
    __table_args__ = (
        Index("uq_users_email_lower", text("lower(email)"), unique=True),
        CheckConstraint("role <> 'doctor' OR doctor_id IS NOT NULL", name="doctor_role_has_doctor"),
    )

    id: Mapped[uuid.UUID] = mapped_column(
        primary_key=True, default=uuid.uuid4, server_default=text("gen_random_uuid()")
    )
    email: Mapped[str] = mapped_column(Text)
    password_hash: Mapped[str] = mapped_column(Text)
    role: Mapped[UserRole] = mapped_column(
        Enum(UserRole, name="user_role", values_callable=enum_values)
    )
    full_name: Mapped[str | None] = mapped_column(Text)
    doctor_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("doctors.id", ondelete="RESTRICT"), unique=True
    )
    is_active: Mapped[bool] = mapped_column(default=True, server_default=text("true"))
    created_at: Mapped[datetime] = mapped_column(server_default=func.now())
