"""Liveness/readiness endpoint."""

from typing import Annotated

from fastapi import APIRouter, Depends
from sqlalchemy import text
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import Session

from app.core.errors import AppError
from app.db.session import get_session

router = APIRouter()


@router.get("/health")
def health(session: Annotated[Session, Depends(get_session)]) -> dict[str, str]:
    """Return 200 when the app can reach the database, otherwise 503."""
    try:
        session.execute(text("SELECT 1"))
    except SQLAlchemyError as exc:
        raise AppError(503, "service_unavailable", "Database is unavailable") from exc
    return {"status": "ok"}
