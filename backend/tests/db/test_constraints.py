from datetime import UTC, datetime, timedelta

from sqlalchemy import delete
from sqlalchemy.orm import Session

from app.models import AppointmentStatus, Hospital, UserRole
from tests.db.factories import (
    SLOT,
    make_appointment,
    make_doctor,
    make_hospital,
    make_user,
    violates,
)


def test_same_doctor_and_start_time_is_rejected(db_session: Session) -> None:
    hospital = make_hospital(db_session)
    doctor = make_doctor(db_session, [hospital])
    make_appointment(db_session, doctor, hospital)
    with violates(db_session, "uq_appointments_doctor_slot"):
        make_appointment(db_session, doctor, hospital)


def test_double_booking_across_hospitals_is_rejected(db_session: Session) -> None:
    first, second = make_hospital(db_session), make_hospital(db_session)
    doctor = make_doctor(db_session, [first, second])
    make_appointment(db_session, doctor, first)
    with violates(db_session, "uq_appointments_doctor_slot"):
        make_appointment(db_session, doctor, second)


def test_slot_is_free_again_after_cancellation(db_session: Session) -> None:
    hospital = make_hospital(db_session)
    doctor = make_doctor(db_session, [hospital])
    make_appointment(db_session, doctor, hospital, status=AppointmentStatus.CANCELLED)
    make_appointment(db_session, doctor, hospital, status=AppointmentStatus.CANCELLED)
    make_appointment(db_session, doctor, hospital)


def test_slot_is_free_again_after_soft_delete(db_session: Session) -> None:
    hospital = make_hospital(db_session)
    doctor = make_doctor(db_session, [hospital])
    make_appointment(db_session, doctor, hospital, deleted_at=datetime.now(UTC))
    make_appointment(db_session, doctor, hospital)


def test_different_doctors_can_share_a_time(db_session: Session) -> None:
    hospital = make_hospital(db_session)
    make_appointment(db_session, make_doctor(db_session, [hospital]), hospital)
    make_appointment(db_session, make_doctor(db_session, [hospital]), hospital)


def test_start_time_must_be_on_a_half_hour(db_session: Session) -> None:
    hospital = make_hospital(db_session)
    doctor = make_doctor(db_session, [hospital])
    make_appointment(db_session, doctor, hospital, SLOT + timedelta(minutes=30))
    with violates(db_session, "ck_appointments_slot_aligned"):
        make_appointment(db_session, doctor, hospital, SLOT + timedelta(minutes=15))
    with violates(db_session, "ck_appointments_slot_aligned"):
        make_appointment(db_session, doctor, hospital, SLOT + timedelta(hours=1, seconds=5))


def test_doctor_must_visit_the_hospital(db_session: Session) -> None:
    visited, other = make_hospital(db_session), make_hospital(db_session)
    doctor = make_doctor(db_session, [visited])
    with violates(db_session, "fk_appointments_doctor_hospital"):
        make_appointment(db_session, doctor, other)


def test_anonymous_booking_has_no_creator(db_session: Session) -> None:
    hospital = make_hospital(db_session)
    appointment = make_appointment(db_session, make_doctor(db_session, [hospital]), hospital)
    assert appointment.created_by is None


def test_patient_name_needs_two_characters(db_session: Session) -> None:
    hospital = make_hospital(db_session)
    doctor = make_doctor(db_session, [hospital])
    with violates(db_session, "ck_appointments_patient_name_length"):
        make_appointment(db_session, doctor, hospital, patient_name=" a ")


def test_hospital_with_doctors_cannot_be_deleted(db_session: Session) -> None:
    hospital = make_hospital(db_session)
    make_doctor(db_session, [hospital])
    with violates(db_session, "doctor_hospitals"):
        db_session.execute(delete(Hospital).where(Hospital.id == hospital.id))


def test_hospital_names_are_unique_ignoring_case(db_session: Session) -> None:
    make_hospital(db_session, "City Care")
    with violates(db_session, "uq_hospitals_name_lower"):
        make_hospital(db_session, "city care")


def test_user_emails_are_unique_ignoring_case(db_session: Session) -> None:
    make_user(db_session, email="Staff@Demo.test")
    with violates(db_session, "uq_users_email_lower"):
        make_user(db_session, email="staff@demo.test")


def test_doctor_role_requires_a_doctor_profile(db_session: Session) -> None:
    with violates(db_session, "ck_users_doctor_role_has_doctor"):
        make_user(db_session, role=UserRole.DOCTOR)


def test_a_doctor_profile_has_at_most_one_user(db_session: Session) -> None:
    doctor = make_doctor(db_session, [make_hospital(db_session)])
    make_user(db_session, role=UserRole.DOCTOR, doctor=doctor)
    with violates(db_session, "uq_users_doctor_id"):
        make_user(db_session, role=UserRole.DOCTOR, doctor=doctor)
