"""
Global exception handling middleware.

Catches unhandled exceptions and returns a consistent JSON error response,
preventing raw tracebacks from leaking to clients. No domain-specific
error handling is implemented yet.
"""
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import JSONResponse

from app.core.logging_config import get_logger

logger = get_logger("app.errors")


class ExceptionHandlingMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next):
        try:
            return await call_next(request)
        except Exception as exc:  # noqa: BLE001
            logger.exception("Unhandled exception on %s %s", request.method, request.url.path)
            return JSONResponse(
                status_code=500,
                content={
                    "detail": "Internal server error.",
                    "error_type": exc.__class__.__name__,
                },
            )
