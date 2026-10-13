"""Hospital model."""

import uuid
from datetime import datetime
from typing import TYPE_CHECKING

from sqlalchemy import Index, Text, func, text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base

if TYPE_CHECKING:
    from app.models.doctor import Doctor


class Hospital(Base):
    """A hospital that doctors visit. Names are unique ignoring case."""

    __tablename__ = "hospitals"
    __table_args__ = (Index("uq_hospitals_name_lower", text("lower(name)"), unique=True),)

    id: Mapped[uuid.UUID] = mapped_column(
        primary_key=True, default=uuid.uuid4, server_default=text("gen_random_uuid()")
    )
    name: Mapped[str] = mapped_column(Text)
    created_at: Mapped[datetime] = mapped_column(server_default=func.now())

    doctors: Mapped[list["Doctor"]] = relationship(
        secondary="doctor_hospitals", back_populates="hospitals"
    )
