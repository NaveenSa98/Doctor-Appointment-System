"""Request and response shapes for the staff view of registered patients."""

import uuid

from pydantic import BaseModel, ConfigDict, Field, field_validator

from app.schemas.appointment import AppointmentOut
from app.schemas.common import UtcDatetime


class PatientListQuery(BaseModel):
    """Query string of GET /patients. Unknown parameters are rejected."""

    model_config = ConfigDict(extra="forbid")

    q: str | None = Field(default=None, max_length=100)
    page: int = Field(default=1, ge=1)
    page_size: int = Field(default=20, ge=1, le=100)

    @field_validator("q")
    @classmethod
    def _blank_means_no_search(cls, value: str | None) -> str | None:
        if value is None:
            return None
        return value.strip() or None


class PatientOut(BaseModel):
    """A registered patient. For a doctor, the booking numbers count only bookings with them."""

    id: uuid.UUID
    full_name: str | None
    email: str
    is_active: bool
    created_at: UtcDatetime
    booking_count: int
    last_booking_at: UtcDatetime | None


class PatientDetail(PatientOut):
    """A patient with their bookings, latest first (at most 100)."""

    bookings: list[AppointmentOut]
