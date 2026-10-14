"""Request and response shapes for the admin doctor-management endpoints."""

import uuid
from typing import Annotated, Any, Self

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator

from app.schemas.auth import Email, FullName, NewPassword
from app.schemas.hospital import HospitalOut

# A specialty follows the same rules as a name: trimmed, 2 to 100 characters, no control characters.
Specialty = FullName
HospitalIds = Annotated[list[uuid.UUID], Field(min_length=1, max_length=50)]


def _dedupe(ids: list[uuid.UUID]) -> list[uuid.UUID]:
    return list(dict.fromkeys(ids))


class DoctorAccountIn(BaseModel):
    """The login an admin creates for a doctor: an email and an initial password."""

    model_config = ConfigDict(extra="forbid")

    email: Email
    password: NewPassword


class DoctorCreate(BaseModel):
    """Body of POST /admin/doctors. The account is optional and can be added later."""

    model_config = ConfigDict(extra="forbid")

    full_name: FullName
    specialty: Specialty
    hospital_ids: HospitalIds
    account: DoctorAccountIn | None = None

    @field_validator("hospital_ids")
    @classmethod
    def _unique_hospitals(cls, value: list[uuid.UUID]) -> list[uuid.UUID]:
        return _dedupe(value)


class DoctorUpdate(BaseModel):
    """Body of PATCH /admin/doctors/{id}: any subset of the fields, none of them null."""

    model_config = ConfigDict(extra="forbid")

    full_name: FullName | None = None
    specialty: Specialty | None = None
    hospital_ids: HospitalIds | None = None
    is_active: bool | None = None

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
        if self.hospital_ids is not None:
            self.hospital_ids = _dedupe(self.hospital_ids)
        return self


class AccountUpsert(BaseModel):
    """Body of PUT /admin/doctors/{id}/account: create the login, or change its email/password."""

    model_config = ConfigDict(extra="forbid")

    email: Email | None = None
    password: NewPassword | None = None

    @model_validator(mode="before")
    @classmethod
    def _no_nulls(cls, data: Any) -> Any:
        if isinstance(data, dict) and any(value is None for value in data.values()):
            raise ValueError("fields may not be null")
        return data

    @model_validator(mode="after")
    def _at_least_one_field(self) -> Self:
        if not self.model_fields_set:
            raise ValueError("Provide an email, a password, or both")
        return self


class DoctorAccountOut(BaseModel):
    """A doctor's login, without the password hash."""

    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    email: str
    is_active: bool


class AdminDoctorOut(BaseModel):
    """A doctor as the admin sees them: any status, with their login and booking count."""

    id: uuid.UUID
    full_name: str
    specialty: str
    is_active: bool
    hospitals: list[HospitalOut]
    account: DoctorAccountOut | None
    appointment_count: int
