"""Appointment endpoints. Creating is public; everything else needs sign-in."""

import uuid
from typing import Annotated

from fastapi import APIRouter, Depends, Query, Response

from app.api.v1.deps import (
    CurrentUser,
    NowDep,
    SessionDep,
    SettingsDep,
    booking_rate_limit,
    get_optional_user,
)
from app.models import Appointment, User
from app.schemas.appointment import (
    AppointmentCreate,
    AppointmentListQuery,
    AppointmentOut,
    AppointmentStatsOut,
    AppointmentStatsQuery,
    AppointmentUpdate,
)
from app.schemas.common import Page
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
    settings: SettingsDep,
    now: NowDep,
    user: Annotated[User | None, Depends(get_optional_user)],
) -> Appointment:
    """Book an appointment. No sign-in needed; a signed-in user gets a pre-filled doctor."""
    appointment = appointment_service.create_appointment(
        session, user, body, now, settings.clinic_utc_offset_minutes
    )
    response.headers["Location"] = f"/api/v1/appointments/{appointment.id}"
    return appointment


@router.get("", response_model=Page[AppointmentOut])
def list_appointments(
    query: Annotated[AppointmentListQuery, Query()], session: SessionDep, user: CurrentUser
) -> Page[AppointmentOut]:
    """Search, filter, sort and paginate appointments. Doctors only see their own."""
    return appointment_service.list_appointments(session, user, query)


@router.get("/stats", response_model=AppointmentStatsOut)
def appointment_stats(
    query: Annotated[AppointmentStatsQuery, Query()], session: SessionDep, user: CurrentUser
) -> AppointmentStatsOut:
    """Counts per status. Declared before `/{appointment_id}` so "stats" is not read as an id."""
    return appointment_service.appointment_stats(session, user, query)


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
    settings: SettingsDep,
    now: NowDep,
    user: CurrentUser,
) -> Appointment:
    """Change any subset of an appointment's fields."""
    return appointment_service.update_appointment(
        session, user, appointment_id, body, now, settings.clinic_utc_offset_minutes
    )


@router.delete("/{appointment_id}", status_code=204, response_class=Response)
def delete_appointment(
    appointment_id: uuid.UUID, session: SessionDep, now: NowDep, user: CurrentUser
) -> Response:
    """Soft-delete an appointment."""
    appointment_service.delete_appointment(session, user, appointment_id, now)
    return Response(status_code=204)
