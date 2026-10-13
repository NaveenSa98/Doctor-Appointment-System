"""Application factory."""

from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api.v1 import health
from app.api.v1.router import api_v1_router
from app.core.config import Settings, get_settings
from app.core.errors import register_error_handlers
from app.core.logging import configure_logging, register_middleware
from app.core.ratelimit import RateLimiter
from app.db.session import make_engine


def create_app(settings: Settings | None = None) -> FastAPI:
    """Build the FastAPI app. Run with: uvicorn app.main:create_app --factory."""
    settings = settings or get_settings()
    configure_logging(settings.log_level)
    engine = make_engine(settings)

    @asynccontextmanager
    async def lifespan(_app: FastAPI) -> AsyncIterator[None]:
        yield
        engine.dispose()

    app = FastAPI(title="Doctor Appointment API", lifespan=lifespan)
    app.state.settings = settings
    app.state.engine = engine
    app.state.rate_limiter = RateLimiter()

    register_error_handlers(app)
    register_middleware(app)
    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.cors_origin_list,
        allow_methods=["GET", "POST", "PATCH", "DELETE", "OPTIONS"],
        allow_headers=["Authorization", "Content-Type"],
    )

    app.include_router(health.router)
    app.include_router(api_v1_router, prefix="/api/v1")
    return app
