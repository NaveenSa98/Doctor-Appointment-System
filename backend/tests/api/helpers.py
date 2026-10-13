"""Small helpers for API tests."""

from datetime import datetime, timedelta
from typing import Any

from app.core.clock import utcnow
from app.core.security import create_access_token
from app.models import Doctor, Hospital, User
from tests.conftest import VALID_SECRET


def auth_header(user: User) -> dict[str, str]:
    """A valid Authorization header for the user."""
    token = create_access_token(
        user.id, user.role.value, VALID_SECRET, utcnow(), timedelta(minutes=30)
    )
    return {"Authorization": f"Bearer {token}"}


def future_slot(days: int = 3, hour: int = 9, minute: int = 0) -> datetime:
    """A bookable start time: `days` from now, on the given hour and minute (UTC)."""
    base = utcnow() + timedelta(days=days)
    return base.replace(hour=hour, minute=minute, second=0, microsecond=0)


def iso(value: datetime) -> str:
    """ISO-8601 UTC with a trailing Z, as the API sends and accepts it."""
    return value.isoformat().replace("+00:00", "Z")


def booking(
    doctor: Doctor | None, hospital: Hospital, start: datetime, **extra: Any
) -> dict[str, Any]:
    """A valid POST /appointments body."""
    body: dict[str, Any] = {
        "patient_name": "Jane Doe",
        "hospital_id": str(hospital.id),
        "start_time": iso(start),
        "appointment_type": "consultation",
    }
    if doctor is not None:
        body["doctor_id"] = str(doctor.id)
    body.update(extra)
    return body
