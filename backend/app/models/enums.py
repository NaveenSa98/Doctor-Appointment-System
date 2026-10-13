"""Enumerations stored as native Postgres enum types."""

from enum import Enum, StrEnum


class UserRole(StrEnum):
    """Staff roles."""

    ADMIN = "admin"
    DOCTOR = "doctor"


class AppointmentType(StrEnum):
    """Kinds of appointment."""

    CONSULTATION = "consultation"
    FOLLOW_UP = "follow_up"
    CHECK_UP = "check_up"
    PROCEDURE = "procedure"
    VACCINATION = "vaccination"


class AppointmentStatus(StrEnum):
    """Appointment lifecycle states."""

    SCHEDULED = "scheduled"
    CONFIRMED = "confirmed"
    COMPLETED = "completed"
    CANCELLED = "cancelled"
    NO_SHOW = "no_show"


def enum_values(enum_class: type[Enum]) -> list[str]:
    """Store the enum values (not the member names) in the database."""
    return [str(member.value) for member in enum_class]
