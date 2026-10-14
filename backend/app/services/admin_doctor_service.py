"""Admin management of doctors: profiles, hospitals, logins, deactivating and deleting."""

import uuid

from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.core.errors import AppError, NotFoundError, ValidationFailed
from app.core.security import hash_password
from app.models import Doctor, Hospital, User, UserRole
from app.repositories import (
    appointment_repository,
    doctor_repository,
    hospital_repository,
    session_repository,
    user_repository,
)
from app.schemas.admin import (
    AccountUpsert,
    AdminDoctorOut,
    DoctorAccountIn,
    DoctorAccountOut,
    DoctorCreate,
    DoctorUpdate,
)
from app.schemas.hospital import HospitalOut


def _email_taken() -> AppError:
    return AppError(409, "email_taken", "An account with this email already exists")


def _to_out(doctor: Doctor, account: User | None, appointment_count: int) -> AdminDoctorOut:
    hospitals = sorted(doctor.hospitals, key=lambda hospital: hospital.name.lower())
    return AdminDoctorOut(
        id=doctor.id,
        full_name=doctor.full_name,
        specialty=doctor.specialty,
        is_active=doctor.is_active,
        hospitals=[HospitalOut.model_validate(hospital) for hospital in hospitals],
        account=DoctorAccountOut.model_validate(account) if account else None,
        appointment_count=appointment_count,
    )


def _require_doctor(session: Session, doctor_id: uuid.UUID) -> Doctor:
    doctor = doctor_repository.get(session, doctor_id)
    if doctor is None:
        raise NotFoundError("Doctor not found")
    return doctor


def _present(session: Session, doctor: Doctor) -> AdminDoctorOut:
    counts = appointment_repository.count_live_by_doctor(session)
    account = user_repository.get_by_doctor_id(session, doctor.id)
    return _to_out(doctor, account, counts.get(doctor.id, 0))


def _load_hospitals(session: Session, hospital_ids: list[uuid.UUID]) -> list[Hospital]:
    hospitals = hospital_repository.get_many(session, hospital_ids)
    missing = set(hospital_ids) - {hospital.id for hospital in hospitals}
    if missing:
        raise ValidationFailed("hospital_ids", "contains a hospital that does not exist")
    return hospitals


def _new_login(session: Session, doctor: Doctor, data: DoctorAccountIn) -> User:
    if user_repository.get_by_email(session, data.email) is not None:
        raise _email_taken()
    user = User(
        email=data.email,
        full_name=doctor.full_name,
        password_hash=hash_password(data.password),
        role=UserRole.DOCTOR,
        doctor_id=doctor.id,
    )
    user_repository.add(session, user)
    return user


def list_doctors(session: Session) -> list[AdminDoctorOut]:
    """Every doctor with their login and live booking count."""
    doctors = doctor_repository.list_all(session)
    accounts = user_repository.by_doctor_ids(session, [doctor.id for doctor in doctors])
    counts = appointment_repository.count_live_by_doctor(session)
    return [_to_out(d, accounts.get(d.id), counts.get(d.id, 0)) for d in doctors]


def get_doctor(session: Session, doctor_id: uuid.UUID) -> AdminDoctorOut:
    """One doctor as the admin sees them."""
    return _present(session, _require_doctor(session, doctor_id))


def create_doctor(session: Session, data: DoctorCreate) -> AdminDoctorOut:
    """Create a doctor, link their hospitals and, if given, create their login."""
    doctor = Doctor(full_name=data.full_name, specialty=data.specialty)
    hospitals = _load_hospitals(session, data.hospital_ids)
    try:
        with session.begin_nested():
            # Add the doctor before linking hospitals, so the link is cascaded from a
            # doctor that is already in the session.
            doctor_repository.add(session, doctor)
            doctor.hospitals = hospitals
            session.flush()
            if data.account is not None:
                _new_login(session, doctor, data.account)
    except IntegrityError as exc:  # two admins creating the same email at once
        raise _email_taken() from exc
    session.commit()
    return _present(session, doctor)


def _check_hospitals_removable(session: Session, doctor: Doctor, wanted: list[Hospital]) -> None:
    removed = {hospital.id for hospital in doctor.hospitals} - {hospital.id for hospital in wanted}
    if not removed:
        return
    if session_repository.hospitals_with_sessions(session, doctor.id, list(removed)):
        raise AppError(
            409,
            "hospital_has_sessions",
            "This doctor has weekly sessions at a hospital you are removing. Remove them first.",
        )
    if appointment_repository.hospitals_in_use(session, doctor.id, list(removed)):
        raise AppError(
            409,
            "hospital_in_use",
            "This doctor has appointments at a hospital you are removing. "
            "Deactivate the doctor instead, or keep that hospital.",
        )


def update_doctor(session: Session, doctor_id: uuid.UUID, data: DoctorUpdate) -> AdminDoctorOut:
    """Change a doctor's profile, hospitals, or active state (which also gates their login)."""
    doctor = _require_doctor(session, doctor_id)
    account = user_repository.get_by_doctor_id(session, doctor.id)
    if data.full_name is not None:
        doctor.full_name = data.full_name
        if account is not None:
            account.full_name = data.full_name
    if data.specialty is not None:
        doctor.specialty = data.specialty
    if data.hospital_ids is not None:
        wanted = _load_hospitals(session, data.hospital_ids)
        _check_hospitals_removable(session, doctor, wanted)
        doctor.hospitals = wanted
    if data.is_active is not None:
        doctor.is_active = data.is_active
        if account is not None:
            account.is_active = data.is_active
    session.commit()
    return _present(session, doctor)


def set_account(session: Session, doctor_id: uuid.UUID, data: AccountUpsert) -> AdminDoctorOut:
    """Create the doctor's login (email and password), or change its email and/or password."""
    doctor = _require_doctor(session, doctor_id)
    account = user_repository.get_by_doctor_id(session, doctor.id)
    try:
        with session.begin_nested():
            if account is None:
                if data.email is None or data.password is None:
                    raise ValidationFailed("password", "email and password are both needed")
                _new_login(
                    session, doctor, DoctorAccountIn(email=data.email, password=data.password)
                )
            else:
                _change_login(session, account, data)
    except IntegrityError as exc:
        raise _email_taken() from exc
    session.commit()
    return _present(session, doctor)


def _change_login(session: Session, account: User, data: AccountUpsert) -> None:
    if data.password is not None:
        account.password_hash = hash_password(data.password)
    if data.email is not None and data.email.lower() != account.email.lower():
        if user_repository.get_by_email(session, data.email) is not None:
            raise _email_taken()
        account.email = data.email
    session.flush()


def delete_doctor(session: Session, doctor_id: uuid.UUID) -> None:
    """Delete a doctor and their login. Refused (409) once any appointment refers to them."""
    doctor = _require_doctor(session, doctor_id)
    if appointment_repository.has_any_for_doctor(session, doctor.id):
        raise AppError(
            409,
            "doctor_has_appointments",
            "This doctor has appointments, so they cannot be deleted. Deactivate them instead.",
        )
    account = user_repository.get_by_doctor_id(session, doctor.id)
    if account is not None:
        user_repository.delete(session, account)
    doctor_repository.delete(session, doctor)
    session.commit()
