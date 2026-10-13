"""PII-safe request logging and response hardening middleware.

Logs only the method, route template, status and duration. Query strings, bodies,
headers and tokens are never logged, because search terms and names are personal data.
"""

import logging
import time
import uuid
from collections.abc import Awaitable, Callable

from fastapi import FastAPI, Request, Response

logger = logging.getLogger("app.request")


def configure_logging(level: str) -> None:
    """Configure root logging once."""
    logging.basicConfig(level=level, format="%(asctime)s %(levelname)s %(name)s %(message)s")


def _route_template(request: Request) -> str:
    route = request.scope.get("route")
    return str(getattr(route, "path", "unmatched"))


def register_middleware(app: FastAPI) -> None:
    """Install request logging, request ids and security headers."""

    @app.middleware("http")
    async def request_context(
        request: Request, call_next: Callable[[Request], Awaitable[Response]]
    ) -> Response:
        request_id = uuid.uuid4().hex
        started = time.perf_counter()
        status = 500
        try:
            response = await call_next(request)
            status = response.status_code
        finally:
            elapsed_ms = (time.perf_counter() - started) * 1000
            logger.info(
                "%s %s -> %s in %.1f ms [%s]",
                request.method,
                _route_template(request),
                status,
                elapsed_ms,
                request_id,
            )
        response.headers["X-Request-ID"] = request_id
        response.headers["X-Content-Type-Options"] = "nosniff"
        response.headers["Referrer-Policy"] = "no-referrer"
        return response
