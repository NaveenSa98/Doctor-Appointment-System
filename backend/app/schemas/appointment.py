"""Appointment request and response shapes, with all input validation."""

import unicodedata
import uuid
from datetime import UTC, datetime
from typing import Annotated, Any, Self

from pydantic import (
    AfterValidator,
    AwareDatetime,
    BaseModel,
    ConfigDict,
    Field,
    field_validator,
    model_validator,
)

from app.models import AppointmentSort, AppointmentStatus, AppointmentType
from app.schemas.common import UtcDatetime
from app.schemas.doctor import DoctorBrief
from app.schemas.hospital import HospitalOut


def _clean_patient_name(value: str) -> str:
    cleaned = value.strip()
    if not 2 <= len(cleaned) <= 100:
        raise ValueError("must be 2 to 100 characters")
    if any(unicodedata.category(char).startswith("C") for char in cleaned):
        raise ValueError("must not contain control characters")
    return cleaned


def _validate_slot(value: datetime) -> datetime:
    """Require a timezone and a :00 or :30 start (in UTC); return the UTC datetime."""
    if value.tzinfo is None or value.utcoffset() is None:
        raise ValueError("must include a timezone, for example 2030-01-15T09:00:00Z")
    utc_value = value.astimezone(UTC)
    if utc_value.second or utc_value.microsecond or utc_value.minute not in (0, 30):
        raise ValueError("must start on the hour or half hour")
    return utc_value


PatientName = Annotated[str, AfterValidator(_clean_patient_name)]
SlotStart = Annotated[datetime, AfterValidator(_validate_slot)]


class AppointmentCreate(BaseModel):
    """Body of POST /appointments."""

    model_config = ConfigDict(extra="forbid")

    patient_name: PatientName
    doctor_id: uuid.UUID | None = None
    hospital_id: uuid.UUID
    start_time: SlotStart
    appointment_type: AppointmentType
    status: AppointmentStatus | None = None


class AppointmentUpdate(BaseModel):
    """Body of PATCH /appointments/{id}: any subset of the fields, none of them null."""

    model_config = ConfigDict(extra="forbid")

    patient_name: PatientName | None = None
    doctor_id: uuid.UUID | None = None
    hospital_id: uuid.UUID | None = None
    start_time: SlotStart | None = None
    appointment_type: AppointmentType | None = None
    status: AppointmentStatus | None = None

    @field_validator("*", mode="before")
    @classmethod
    def _no_nulls(cls, value: Any) -> Any:
        if value is None:
            raise ValueError("may not be null")
        return value

    @model_validator(mode="after")
    def _at_least_one_field(self) -> Self:
        if not self.model_fields_set:
            raise ValueError("Provide at least one field to update")
        return self


class AppointmentListQuery(BaseModel):
    """Query string of GET /appointments. Unknown parameters are rejected."""

    model_config = ConfigDict(extra="forbid")

    q: str | None = Field(default=None, max_length=100)
    doctor_id: uuid.UUID | None = None
    hospital_id: uuid.UUID | None = None
    status: list[AppointmentStatus] = Field(default_factory=list)
    type: list[AppointmentType] = Field(default_factory=list)
    date_from: AwareDatetime | None = None
    date_to: AwareDatetime | None = None
    sort: AppointmentSort = AppointmentSort.START_TIME
    page: int = Field(default=1, ge=1)
    page_size: int = Field(default=20, ge=1, le=100)

    @field_validator("q")
    @classmethod
    def _blank_means_no_search(cls, value: str | None) -> str | None:
        if value is None:
            return None
        return value.strip() or None


class AppointmentStatsQuery(BaseModel):
    """Query string of GET /appointments/stats. Unknown parameters are rejected."""

    model_config = ConfigDict(extra="forbid")

    doctor_id: uuid.UUID | None = None
    date_from: AwareDatetime | None = None
    date_to: AwareDatetime | None = None


class AppointmentStatsOut(BaseModel):
    """Live appointment counts: the total and one count per status (zero when none)."""

    total: int
    by_status: dict[AppointmentStatus, int]


class AppointmentOut(BaseModel):
    """An appointment with its doctor and hospital."""

    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    patient_name: str
    doctor: DoctorBrief
    hospital: HospitalOut
    start_time: UtcDatetime
    appointment_type: AppointmentType
    status: AppointmentStatus
    created_at: UtcDatetime
    updated_at: UtcDatetime
