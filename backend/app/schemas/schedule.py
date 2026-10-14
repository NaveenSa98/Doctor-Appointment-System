"""Request and response shapes for weekly doctor sessions and bookable slots."""

import datetime as dt
import uuid
from datetime import date, time
from typing import Annotated, Any, Self

from pydantic import (
    AfterValidator,
    BaseModel,
    ConfigDict,
    Field,
    field_serializer,
    model_validator,
)

from app.schemas.common import UtcDatetime
from app.schemas.hospital import HospitalOut


def _half_hour(value: time) -> time:
    if value.tzinfo is not None or value.second or value.microsecond or value.minute not in (0, 30):
        raise ValueError("must be on the hour or half hour, for example 09:00 or 09:30")
    return value


HalfHour = Annotated[time, AfterValidator(_half_hour)]
Weekday = Annotated[int, Field(ge=0, le=6, description="Monday is 0, Sunday is 6")]


def _ordered(start: time, end: time) -> None:
    if end <= start:
        raise ValueError("end_time must be after start_time")


class SessionCreate(BaseModel):
    """Body of POST /admin/doctors/{id}/sessions."""

    model_config = ConfigDict(extra="forbid")

    hospital_id: uuid.UUID
    weekday: Weekday
    start_time: HalfHour
    end_time: HalfHour

    @model_validator(mode="after")
    def _check_order(self) -> Self:
        _ordered(self.start_time, self.end_time)
        return self


class SessionUpdate(BaseModel):
    """Body of PATCH /admin/sessions/{id}: any subset, none of them null."""

    model_config = ConfigDict(extra="forbid")

    hospital_id: uuid.UUID | None = None
    weekday: Weekday | None = None
    start_time: HalfHour | None = None
    end_time: HalfHour | None = None

    @model_validator(mode="before")
    @classmethod
    def _no_nulls(cls, data: Any) -> Any:
        if isinstance(data, dict) and any(value is None for value in data.values()):
            raise ValueError("fields may not be null")
        return data

    @model_validator(mode="after")
    def _at_least_one_field(self) -> Self:
        if not self.model_fields_set:
            raise ValueError("Provide at least one field to update")
        if self.start_time is not None and self.end_time is not None:
            _ordered(self.start_time, self.end_time)
        return self


class SkipDateCreate(BaseModel):
    """Body of POST /admin/sessions/{id}/skipped-dates."""

    model_config = ConfigDict(extra="forbid")

    date: dt.date
    reason: str | None = Field(default=None, max_length=200)


class SkippedDateOut(BaseModel):
    """One day a session does not run."""

    model_config = ConfigDict(from_attributes=True)

    on_date: date
    reason: str | None


class SessionOut(BaseModel):
    """A weekly session in clinic time, with the days it is skipped."""

    id: uuid.UUID
    hospital: HospitalOut
    weekday: int
    start_time: time
    end_time: time
    skipped: list[SkippedDateOut]

    @field_serializer("start_time", "end_time")
    def _clock(self, value: time) -> str:
        return value.strftime("%H:%M")


class SessionsOut(BaseModel):
    """A doctor's whole schedule. `utc_offset_minutes` is the clinic clock the times are in."""

    doctor_id: uuid.UUID
    utc_offset_minutes: int
    sessions: list[SessionOut]


class SlotsOut(BaseModel):
    """Start times a patient may pick for one doctor at one hospital.

    `restricted` is False when the doctor has no sessions at all: any time is accepted and
    `slots` is empty (the app falls back to its default opening hours).
    """

    doctor_id: uuid.UUID
    hospital_id: uuid.UUID
    restricted: bool
    slots: list[UtcDatetime]
