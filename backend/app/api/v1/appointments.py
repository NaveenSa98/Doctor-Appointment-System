"""Appointment endpoints. Creating is public; everything else needs sign-in."""

import uuid
from typing import Annotated

from fastapi import APIRouter, Depends, Response

from app.api.v1.deps import (
    CurrentUser,
    NowDep,
    SessionDep,
    booking_rate_limit,
    get_optional_user,
)
from app.models import Appointment, User
from app.schemas.appointment import AppointmentCreate, AppointmentOut, AppointmentUpdate
from app.services import appointment_service

router = APIRouter(prefix="/appointments", tags=["appointments"])


@router.post(
    "",
    response_model=AppointmentOut,
    status_code=201,
    dependencies=[Depends(booking_rate_limit)],
)
def create_appointment(
    body: AppointmentCreate,
    response: Response,
    session: SessionDep,
    now: NowDep,
    user: Annotated[User | None, Depends(get_optional_user)],
) -> Appointment:
    """Book an appointment. No sign-in needed; a signed-in user gets a pre-filled doctor."""
    appointment = appointment_service.create_appointment(session, user, body, now)
    response.headers["Location"] = f"/api/v1/appointments/{appointment.id}"
    return appointment


@router.get("/{appointment_id}", response_model=AppointmentOut)
def get_appointment(
    appointment_id: uuid.UUID, session: SessionDep, user: CurrentUser
) -> Appointment:
    """Return one appointment."""
    return appointment_service.get_appointment(session, user, appointment_id)


@router.patch("/{appointment_id}", response_model=AppointmentOut)
def update_appointment(
    appointment_id: uuid.UUID,
    body: AppointmentUpdate,
    session: SessionDep,
    now: NowDep,
    user: CurrentUser,
) -> Appointment:
    """Change any subset of an appointment's fields."""
    return appointment_service.update_appointment(session, user, appointment_id, body, now)


@router.delete("/{appointment_id}", status_code=204, response_class=Response)
def delete_appointment(
    appointment_id: uuid.UUID, session: SessionDep, now: NowDep, user: CurrentUser
) -> Response:
    """Soft-delete an appointment."""
    appointment_service.delete_appointment(session, user, appointment_id, now)
    return Response(status_code=204)
