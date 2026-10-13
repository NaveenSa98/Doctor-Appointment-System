"""Importing this package registers every model on Base.metadata."""

from app.db.base import Base
from app.models.appointment import Appointment
from app.models.doctor import Doctor, doctor_hospitals
from app.models.enums import AppointmentSort, AppointmentStatus, AppointmentType, UserRole
from app.models.hospital import Hospital
from app.models.user import User

__all__ = [
    "Appointment",
    "AppointmentSort",
    "AppointmentStatus",
    "AppointmentType",
    "Base",
    "Doctor",
    "Hospital",
    "User",
    "UserRole",
    "doctor_hospitals",
]
