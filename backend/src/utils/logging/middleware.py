import time

import structlog
from fastapi import Request, Response
from starlette.middleware.base import BaseHTTPMiddleware

from src.utils.logging.context import (
    CORRELATION_ID_HEADER,
    REQUEST_ID_HEADER,
    get_correlation_id,
    get_request_id,
    reset_request_context,
    set_request_context,
)


class RequestLoggingMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next) -> Response:
        set_request_context(
            request.headers.get(REQUEST_ID_HEADER),
            request.headers.get(CORRELATION_ID_HEADER),
        )
        started = time.monotonic()
        structlog.get_logger("app.http").info(
            "request_started",
            method=request.method,
            path=request.url.path,
            request_id=get_request_id(),
            correlation_id=get_correlation_id(),
        )
        try:
            response = await call_next(request)
        except Exception:
            structlog.get_logger("app.http").exception(
                "request_failed",
                method=request.method,
                path=request.url.path,
                duration_ms=round((time.monotonic() - started) * 1000),
                request_id=get_request_id(),
                correlation_id=get_correlation_id(),
            )
            reset_request_context()
            raise
        structlog.get_logger("app.http").info(
            "request_completed",
            method=request.method,
            path=request.url.path,
            status_code=response.status_code,
            duration_ms=round((time.monotonic() - started) * 1000),
            request_id=get_request_id(),
            correlation_id=get_correlation_id(),
        )
        response.headers[REQUEST_ID_HEADER] = get_request_id() or ""
        response.headers[CORRELATION_ID_HEADER] = get_correlation_id() or ""
        reset_request_context()
        return response
