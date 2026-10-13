"""Versioned API router. Feature routers are included here as they are added."""

from fastapi import APIRouter

from app.api.v1 import appointments, auth, doctors, hospitals

api_v1_router = APIRouter()
api_v1_router.include_router(auth.router)
api_v1_router.include_router(hospitals.router)
api_v1_router.include_router(doctors.router)
api_v1_router.include_router(appointments.router)
