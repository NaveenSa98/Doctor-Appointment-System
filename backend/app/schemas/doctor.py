"""Doctor response shapes."""

import uuid

from pydantic import BaseModel, ConfigDict, field_validator

from app.schemas.common import UtcDatetime
from app.schemas.hospital import HospitalOut


class DoctorBrief(BaseModel):
    """A doctor as shown inside an appointment."""

    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    full_name: str
    specialty: str


class DoctorOut(DoctorBrief):
    """A doctor with the hospitals they visit (sorted by name)."""

    hospitals: list[HospitalOut]

    @field_validator("hospitals")
    @classmethod
    def _sort_hospitals(cls, value: list[HospitalOut]) -> list[HospitalOut]:
        return sorted(value, key=lambda hospital: hospital.name.lower())


class AvailabilityOut(BaseModel):
    """Start times already taken for a doctor. Contains no patient data."""

    doctor_id: uuid.UUID
    taken: list[UtcDatetime]
