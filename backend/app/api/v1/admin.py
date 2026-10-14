"""Admin-only endpoints: manage doctors and their logins."""

import uuid
from datetime import date

from fastapi import APIRouter, Depends, Response

from app.api.v1.deps import NowDep, SessionDep, SettingsDep, require_role
from app.models import UserRole
from app.schemas.admin import AccountUpsert, AdminDoctorOut, DoctorCreate, DoctorUpdate
from app.schemas.schedule import (
    SessionCreate,
    SessionOut,
    SessionUpdate,
    SkipDateCreate,
)
from app.services import admin_doctor_service, schedule_service

router = APIRouter(
    prefix="/admin", tags=["admin"], dependencies=[Depends(require_role(UserRole.ADMIN))]
)


@router.get("/doctors", response_model=list[AdminDoctorOut])
def list_doctors(session: SessionDep) -> list[AdminDoctorOut]:
    """Every doctor, active or not, with their login and booking count."""
    return admin_doctor_service.list_doctors(session)


@router.post("/doctors", response_model=AdminDoctorOut, status_code=201)
def create_doctor(body: DoctorCreate, session: SessionDep, response: Response) -> AdminDoctorOut:
    """Add a doctor, optionally with a login."""
    created = admin_doctor_service.create_doctor(session, body)
    response.headers["Location"] = f"/api/v1/admin/doctors/{created.id}"
    return created


@router.get("/doctors/{doctor_id}", response_model=AdminDoctorOut)
def get_doctor(doctor_id: uuid.UUID, session: SessionDep) -> AdminDoctorOut:
    """One doctor."""
    return admin_doctor_service.get_doctor(session, doctor_id)


@router.patch("/doctors/{doctor_id}", response_model=AdminDoctorOut)
def update_doctor(doctor_id: uuid.UUID, body: DoctorUpdate, session: SessionDep) -> AdminDoctorOut:
    """Edit a doctor, their hospitals, or deactivate/reactivate them."""
    return admin_doctor_service.update_doctor(session, doctor_id, body)


@router.put("/doctors/{doctor_id}/account", response_model=AdminDoctorOut)
def set_doctor_account(
    doctor_id: uuid.UUID, body: AccountUpsert, session: SessionDep
) -> AdminDoctorOut:
    """Create the doctor's login, or change its email and/or reset its password."""
    return admin_doctor_service.set_account(session, doctor_id, body)


@router.delete("/doctors/{doctor_id}", status_code=204, response_class=Response)
def delete_doctor(doctor_id: uuid.UUID, session: SessionDep) -> Response:
    """Delete a doctor who has no appointments (otherwise deactivate them)."""
    admin_doctor_service.delete_doctor(session, doctor_id)
    return Response(status_code=204)


# ---- weekly sessions -------------------------------------------------------------------------


@router.post("/doctors/{doctor_id}/sessions", response_model=SessionOut, status_code=201)
def create_session(doctor_id: uuid.UUID, body: SessionCreate, session: SessionDep) -> SessionOut:
    """Add a weekly session (clinic time) at one of the doctor's hospitals."""
    return schedule_service.create_session(session, doctor_id, body)


@router.patch("/sessions/{session_id}", response_model=SessionOut)
def update_session(
    session_id: uuid.UUID,
    body: SessionUpdate,
    session: SessionDep,
    settings: SettingsDep,
    now: NowDep,
) -> SessionOut:
    """Change a session's hospital, weekday or hours."""
    return schedule_service.update_session(
        session, session_id, body, now, settings.clinic_utc_offset_minutes
    )


@router.delete("/sessions/{session_id}", status_code=204, response_class=Response)
def delete_session(
    session_id: uuid.UUID, session: SessionDep, settings: SettingsDep, now: NowDep
) -> Response:
    """Remove a weekly session (refused while upcoming bookings depend on it)."""
    schedule_service.delete_session(session, session_id, now, settings.clinic_utc_offset_minutes)
    return Response(status_code=204)


@router.post("/sessions/{session_id}/skipped-dates", response_model=SessionOut, status_code=201)
def skip_date(
    session_id: uuid.UUID,
    body: SkipDateCreate,
    session: SessionDep,
    settings: SettingsDep,
    now: NowDep,
) -> SessionOut:
    """Take one day out of a weekly session."""
    return schedule_service.skip_date(
        session, session_id, body, now, settings.clinic_utc_offset_minutes
    )


@router.delete("/sessions/{session_id}/skipped-dates/{day}", response_model=SessionOut)
def restore_date(session_id: uuid.UUID, day: date, session: SessionDep) -> SessionOut:
    """Put a skipped day back."""
    return schedule_service.restore_date(session, session_id, day)
