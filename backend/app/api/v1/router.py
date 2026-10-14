"""Versioned API router. Feature routers are included here as they are added."""

from fastapi import APIRouter

from app.api.v1 import admin, appointments, auth, doctors, hospitals, patients

api_v1_router = APIRouter()
api_v1_router.include_router(auth.router)
api_v1_router.include_router(admin.router)
api_v1_router.include_router(hospitals.router)
api_v1_router.include_router(doctors.router)
api_v1_router.include_router(appointments.router)
api_v1_router.include_router(patients.router)
