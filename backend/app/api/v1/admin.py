"""Admin-only endpoints: manage doctors and their logins."""

import uuid

from fastapi import APIRouter, Depends, Response

from app.api.v1.deps import SessionDep, require_role
from app.models import UserRole
from app.schemas.admin import AccountUpsert, AdminDoctorOut, DoctorCreate, DoctorUpdate
from app.services import admin_doctor_service

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
