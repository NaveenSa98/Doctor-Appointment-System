"""Load synthetic demo data. Safe to run repeatedly: existing rows are kept.

Run from backend/ with: uv run python -m scripts.seed
All names, hospitals and accounts are fictional.
"""

import random
from dataclasses import dataclass
from datetime import datetime, timedelta
from typing import Any

from pwdlib import PasswordHash
from sqlalchemy import create_engine, func, select
from sqlalchemy.orm import Session

from app.core.clock import utcnow
from app.core.config import get_settings
from app.models import (
    Appointment,
    AppointmentStatus,
    AppointmentType,
    Doctor,
    Hospital,
    User,
    UserRole,
)

DEMO_PASSWORD = "demo-password-123"
ADMIN_EMAIL = "admin@demo.test"
APPOINTMENT_COUNT = 60

HOSPITALS = [
    "Lakeside General Hospital",
    "Hillcrest Medical Centre",
    "Riverside Clinic",
    "Harbour View Hospital",
]

# (full name, specialty, indexes into HOSPITALS)
DOCTORS = [
    ("Dr. Amal Perera", "Cardiology", [0, 1]),
    ("Dr. Nimali Silva", "Pediatrics", [0]),
    ("Dr. Kasun Fernando", "Orthopedics", [1, 2, 3]),
    ("Dr. Ishara Jayasuriya", "Dermatology", [2]),
    ("Dr. Ruwan Wijesinghe", "General Medicine", [0, 3]),
    ("Dr. Sanduni Gunawardena", "ENT", [1, 3]),
]

FIRST_NAMES = ["Anika", "Binura", "Chamari", "Dinesh", "Eshani", "Farhan", "Gayan", "Hiruni"]
LAST_NAMES = ["Abeysekara", "Bandara", "Cooray", "Dissanayake", "Edirisinghe", "Karunaratne"]


@dataclass
class SeedResult:
    """Row counts after seeding."""

    hospitals: int
    doctors: int
    users: int
    appointments: int


def _count(session: Session, model: Any) -> int:
    return session.scalar(select(func.count()).select_from(model)) or 0


def _email_for(doctor_name: str) -> str:
    parts = doctor_name.removeprefix("Dr. ").lower().split()
    return f"{'.'.join(parts)}@demo.test"


def _get_or_create_hospital(session: Session, name: str) -> Hospital:
    hospital = session.scalar(select(Hospital).where(func.lower(Hospital.name) == name.lower()))
    if hospital is None:
        hospital = Hospital(name=name)
        session.add(hospital)
    return hospital


def _get_or_create_doctor(session: Session, name: str, specialty: str) -> Doctor:
    doctor = session.scalar(select(Doctor).where(Doctor.full_name == name))
    if doctor is None:
        doctor = Doctor(full_name=name, specialty=specialty)
        session.add(doctor)
    return doctor


def _ensure_user(
    session: Session, email: str, role: UserRole, password_hash: str, doctor: Doctor | None
) -> User:
    user = session.scalar(select(User).where(func.lower(User.email) == email))
    if user is None:
        user = User(
            email=email,
            password_hash=password_hash,
            role=role,
            doctor_id=doctor.id if doctor else None,
        )
        session.add(user)
    return user


def _seed_appointments(
    session: Session,
    rng: random.Random,
    now: datetime,
    doctors: list[Doctor],
    admin: User,
) -> None:
    midnight = now.replace(hour=0, minute=0, second=0, microsecond=0)
    slots = [timedelta(hours=9, minutes=30 * i) for i in range(16)]
    used: set[tuple[object, datetime]] = set()
    created = 0
    while created < APPOINTMENT_COUNT:
        doctor = rng.choice(doctors)
        start = midnight + timedelta(days=rng.randint(-10, 20)) + rng.choice(slots)
        if (doctor.id, start) in used:
            continue
        used.add((doctor.id, start))
        past = start < now
        status = rng.choice(
            [AppointmentStatus.COMPLETED] * 3
            + [AppointmentStatus.NO_SHOW, AppointmentStatus.CANCELLED]
            if past
            else [AppointmentStatus.SCHEDULED] * 3
            + [AppointmentStatus.CONFIRMED] * 2
            + [AppointmentStatus.CANCELLED]
        )
        session.add(
            Appointment(
                patient_name=f"{rng.choice(FIRST_NAMES)} {rng.choice(LAST_NAMES)}",
                doctor_id=doctor.id,
                hospital_id=rng.choice(doctor.hospitals).id,
                start_time=start,
                appointment_type=rng.choice(list(AppointmentType)),
                status=status,
                created_by=admin.id if rng.random() < 0.5 else None,
            )
        )
        created += 1


def seed(session: Session, now: datetime | None = None, rng_seed: int = 42) -> SeedResult:
    """Insert demo hospitals, doctors, accounts and appointments that are not there yet."""
    now = now or utcnow()
    rng = random.Random(rng_seed)

    hospitals = [_get_or_create_hospital(session, name) for name in HOSPITALS]
    doctors = [_get_or_create_doctor(session, name, spec) for name, spec, _ in DOCTORS]
    session.flush()

    for doctor, (_, _, hospital_indexes) in zip(doctors, DOCTORS, strict=True):
        for index in hospital_indexes:
            if hospitals[index] not in doctor.hospitals:
                doctor.hospitals.append(hospitals[index])

    # One hash is reused for every demo account; hashing is deliberately slow.
    password_hash = PasswordHash.recommended().hash(DEMO_PASSWORD)
    admin = _ensure_user(session, ADMIN_EMAIL, UserRole.ADMIN, password_hash, None)
    for doctor in doctors:
        _ensure_user(session, _email_for(doctor.full_name), UserRole.DOCTOR, password_hash, doctor)
    session.flush()

    if _count(session, Appointment) == 0:
        _seed_appointments(session, rng, now, doctors, admin)
    session.flush()

    return SeedResult(
        hospitals=_count(session, Hospital),
        doctors=_count(session, Doctor),
        users=_count(session, User),
        appointments=_count(session, Appointment),
    )


def main() -> None:
    """Seed the database configured in backend/.env."""
    settings = get_settings()
    engine = create_engine(settings.database_url_migrations or settings.database_url)
    with Session(engine) as session, session.begin():
        result = seed(session)
    print(
        f"Seeded: {result.hospitals} hospitals, {result.doctors} doctors, "
        f"{result.users} users, {result.appointments} appointments."
    )
    print(f"Demo login: {ADMIN_EMAIL} or any doctor account, password: {DEMO_PASSWORD}")


if __name__ == "__main__":
    main()
