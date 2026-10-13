"""Standard error shape: {"error": {"code", "message", "details"?}}."""

import logging
from typing import Any

from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from starlette.exceptions import HTTPException as StarletteHTTPException

logger = logging.getLogger("app.errors")

_STATUS_CODES = {
    400: "bad_request",
    401: "unauthorized",
    403: "forbidden",
    404: "not_found",
    405: "method_not_allowed",
    409: "conflict",
    429: "rate_limited",
}


class AppError(Exception):
    """Domain error mapped to the standard error response."""

    def __init__(
        self,
        status_code: int,
        code: str,
        message: str,
        details: list[dict[str, str]] | None = None,
        headers: dict[str, str] | None = None,
    ) -> None:
        super().__init__(message)
        self.status_code = status_code
        self.code = code
        self.message = message
        self.details = details
        self.headers = headers


def unauthorized(message: str = "Authentication required") -> AppError:
    """A 401 that tells clients to send a Bearer token."""
    return AppError(401, "unauthorized", message, headers={"WWW-Authenticate": "Bearer"})


class NotFoundError(AppError):
    """The resource does not exist, or the caller may not know that it does."""

    def __init__(self, message: str = "Not found") -> None:
        super().__init__(404, "not_found", message)


class ForbiddenError(AppError):
    """The caller is signed in but not allowed to do this."""

    def __init__(self, message: str = "You do not have access to this resource") -> None:
        super().__init__(403, "forbidden", message)


class SlotConflictError(AppError):
    """The doctor already has an active appointment at that time."""

    def __init__(self) -> None:
        super().__init__(409, "slot_conflict", "The doctor already has an appointment at that time")


class ValidationFailed(AppError):
    """A business-rule validation failure on a single field (422)."""

    def __init__(self, field: str, message: str) -> None:
        super().__init__(
            422,
            "validation_error",
            "Request validation failed",
            [{"field": field, "message": message}],
        )


def error_response(
    status_code: int,
    code: str,
    message: str,
    details: list[dict[str, str]] | None = None,
    headers: dict[str, str] | None = None,
) -> JSONResponse:
    """Build a JSON response in the standard error shape."""
    error: dict[str, Any] = {"code": code, "message": message}
    if details:
        error["details"] = details
    return JSONResponse(status_code=status_code, content={"error": error}, headers=headers)


async def _app_error_handler(_request: Request, exc: Exception) -> JSONResponse:
    assert isinstance(exc, AppError)
    return error_response(exc.status_code, exc.code, exc.message, exc.details, exc.headers)


async def _http_error_handler(_request: Request, exc: Exception) -> JSONResponse:
    assert isinstance(exc, StarletteHTTPException)
    code = _STATUS_CODES.get(exc.status_code, "http_error")
    message = exc.detail if isinstance(exc.detail, str) else "Request failed"
    return error_response(exc.status_code, code, message, headers=dict(exc.headers or {}))


async def _validation_error_handler(_request: Request, exc: Exception) -> JSONResponse:
    assert isinstance(exc, RequestValidationError)
    details = [
        {
            "field": ".".join(str(part) for part in err["loc"] if part not in ("body", "query")),
            "message": str(err["msg"]),
        }
        for err in exc.errors()
    ]
    return error_response(422, "validation_error", "Request validation failed", details)


async def _unhandled_error_handler(request: Request, exc: Exception) -> JSONResponse:
    # Log the exception type only: messages and tracebacks can contain user data.
    logger.error("Unhandled %s on %s", type(exc).__name__, request.method)
    return error_response(500, "internal_error", "Internal server error")


def register_error_handlers(app: FastAPI) -> None:
    """Install handlers so every error response uses the standard shape."""
    app.add_exception_handler(AppError, _app_error_handler)
    app.add_exception_handler(StarletteHTTPException, _http_error_handler)
    app.add_exception_handler(RequestValidationError, _validation_error_handler)
    app.add_exception_handler(Exception, _unhandled_error_handler)
