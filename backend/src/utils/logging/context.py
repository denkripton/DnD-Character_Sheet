import re
from contextvars import ContextVar
from uuid import uuid4

import structlog.contextvars

REQUEST_ID_HEADER = "X-Request-ID"
CORRELATION_ID_HEADER = "X-Correlation-ID"

_SAFE_ID_PATTERN = re.compile(r"^[A-Za-z0-9_-]{1,128}$")

_request_id_var: ContextVar[str | None] = ContextVar("logging_request_id", default=None)
_correlation_id_var: ContextVar[str | None] = ContextVar(
    "logging_correlation_id", default=None
)


def generate_request_id() -> str:
    return uuid4().hex


def is_valid_request_id(value: object) -> bool:
    return isinstance(value, str) and _SAFE_ID_PATTERN.match(value) is not None


def get_request_id() -> str | None:
    return _request_id_var.get()


def get_correlation_id() -> str | None:
    return _correlation_id_var.get()


def set_request_context(
    request_id: str | None = None,
    correlation_id: str | None = None,
) -> None:
    resolved_request_id = (
        request_id if is_valid_request_id(request_id) else generate_request_id()
    )
    resolved_correlation_id = (
        correlation_id
        if is_valid_request_id(correlation_id)
        else resolved_request_id
    )
    _request_id_var.set(resolved_request_id)
    _correlation_id_var.set(resolved_correlation_id)
    structlog.contextvars.bind_contextvars(
        request_id=resolved_request_id,
        correlation_id=resolved_correlation_id,
    )


def reset_request_context() -> None:
    _request_id_var.set(None)
    _correlation_id_var.set(None)
    structlog.contextvars.unbind_contextvars("request_id", "correlation_id")
