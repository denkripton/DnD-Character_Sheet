import asyncio
import json
import logging
import uuid

import pytest
import structlog
import structlog.contextvars
from fastapi import Request
from src.messaging.contract import create_message
from src.messaging.dispatcher import CommandDispatcher
from src.messaging.enums import MessageType
from src.messaging.enums.constants import AUTH_USER_ID_HEADER
from src.utils.logging import (
    CORRELATION_ID_HEADER,
    REQUEST_ID_HEADER,
    configure_logging,
    get_correlation_id,
    get_request_id,
    is_sensitive_key,
    reset_request_context,
    sanitize_event_dict,
    set_request_context,
)
from src.utils.logging.middleware import RequestLoggingMiddleware
from starlette.responses import PlainTextResponse


@pytest.fixture(autouse=True)
def configured_json_logging():
    configure_logging(
        "INFO", service="test-service", environment="test", json_output=True
    )


def _records(capsys) -> list[dict]:
    out = capsys.readouterr().out
    records = []
    for line in out.splitlines():
        line = line.strip()
        if line:
            records.append(json.loads(line))
    return records


def _event(records: list[dict], name: str) -> dict:
    return next(record for record in records if record["event"] == name)


def test_structlog_emits_json_with_core_fields(capsys):
    structlog.get_logger("unit").info("unit_event", answer=42)

    record = _event(_records(capsys), "unit_event")
    assert record["answer"] == 42
    assert record["level"] == "info"
    assert record["logger"] == "unit"
    assert record["service"] == "test-service"
    assert record["environment"] == "test"
    assert record["timestamp"]


def test_stdlib_logger_renders_as_json(capsys):
    logging.getLogger("stdlib.unit").warning("legacy %s", "message")

    record = _event(_records(capsys), "legacy message")
    assert record["level"] == "warning"
    assert record["logger"] == "stdlib.unit"
    assert record["service"] == "test-service"


def test_request_context_is_bound_into_logs(capsys):
    set_request_context("req-1", "corr-1")
    try:
        structlog.get_logger("unit").info("context_event")
        assert get_request_id() == "req-1"
        assert get_correlation_id() == "corr-1"
    finally:
        reset_request_context()

    record = _event(_records(capsys), "context_event")
    assert record["request_id"] == "req-1"
    assert record["correlation_id"] == "corr-1"

    assert get_request_id() is None
    assert get_correlation_id() is None
    structlog.get_logger("unit").info("after_reset_event")
    assert "request_id" not in _event(_records(capsys), "after_reset_event")


def test_invalid_request_ids_are_replaced(capsys):
    set_request_context("bad id\nwith newline", None)
    try:
        request_id = get_request_id()
        correlation_id = get_correlation_id()
        structlog.get_logger("unit").info("unsafe_header_event")
    finally:
        reset_request_context()

    assert request_id != "bad id\nwith newline"
    assert len(request_id) == 32
    assert correlation_id == request_id

    record = _event(_records(capsys), "unsafe_header_event")
    assert record["request_id"] == request_id


def test_missing_ids_are_generated(capsys):
    set_request_context(None, None)
    try:
        structlog.get_logger("unit").info("generated_ids_event")
    finally:
        reset_request_context()

    record = _event(_records(capsys), "generated_ids_event")
    assert len(record["request_id"]) == 32
    assert record["correlation_id"] == record["request_id"]


def test_sanitize_redacts_sensitive_keys():
    cleaned = sanitize_event_dict(
        {
            "password": "hunter2",
            "api_key": "k-1",
            "Authorization": "Bearer abc",
            "nested": {"refresh_token": "t-1", "safe": "keep"},
            "items": [{"cookie": "sid=1", "name": "ok"}],
            "event": "safe_event",
        }
    )

    assert cleaned["password"] == "[REDACTED]"
    assert cleaned["api_key"] == "[REDACTED]"
    assert cleaned["Authorization"] == "[REDACTED]"
    assert cleaned["nested"]["refresh_token"] == "[REDACTED]"
    assert cleaned["nested"]["safe"] == "keep"
    assert cleaned["items"][0]["cookie"] == "[REDACTED]"
    assert cleaned["items"][0]["name"] == "ok"
    assert cleaned["event"] == "safe_event"


def test_sanitize_redacts_sensitive_values():
    cleaned = sanitize_event_dict(
        {
            "note": "Bearer abc.def",
            "auth": "Authorization: Bearer abc",
            "jwt_note": "eyJhbGciOiJIUzI1NiJ9.eyJzdWIiOiIxIn0.abc123",
            "url": "postgresql://app:s3cret@db:5432/main",
            "line": "connection failed password=hunter2",
            "pem": "-----BEGIN RSA PRIVATE KEY-----",
            "plain": "RabbitMQ connection failed",
        }
    )

    assert cleaned["note"] == "[REDACTED]"
    assert "abc" not in cleaned["auth"]
    assert cleaned["jwt_note"] == "[REDACTED]"
    assert cleaned["url"] == "postgresql://[REDACTED]@db:5432/main"
    assert cleaned["line"] == "connection failed password=[REDACTED]"
    assert cleaned["pem"] == "[REDACTED]"
    assert cleaned["plain"] == "RabbitMQ connection failed"


def test_is_sensitive_key_matches_common_names():
    assert is_sensitive_key("access_token")
    assert is_sensitive_key("BOT_SECRET")
    assert is_sensitive_key("X-Api-Key")
    assert is_sensitive_key("private key")
    assert not is_sensitive_key("request_id")
    assert not is_sensitive_key("duration_ms")


def test_exception_text_is_scrubbed_in_logs(capsys):
    try:
        raise RuntimeError("upstream refused password=hunter2")
    except RuntimeError:
        structlog.get_logger("unit").exception("boom_event", error_type="RuntimeError")

    record = _event(_records(capsys), "boom_event")
    assert record["error_type"] == "RuntimeError"
    assert "RuntimeError" in record["exception"]
    assert "hunter2" not in record["exception"]
    assert "password=[REDACTED]" in record["exception"]


def _request(headers: dict[bytes, bytes] | None = None, path: str = "/characters") -> Request:
    return Request(
        {
            "type": "http",
            "http_version": "1.1",
            "method": "GET",
            "scheme": "http",
            "path": path,
            "raw_path": path.encode(),
            "query_string": b"",
            "headers": headers or [],
            "client": ("127.0.0.1", 50000),
            "server": ("testserver", 80),
        }
    )


def test_request_middleware_logs_lifecycle(capsys):
    middleware = RequestLoggingMiddleware(app=lambda scope, receive, send: None)

    async def call_next(request):
        return PlainTextResponse("ok")

    request = _request(
        [
            (b"x-request-id", b"req-abc"),
            (b"x-correlation-id", b"corr-abc"),
        ]
    )
    response = asyncio.run(middleware.dispatch(request, call_next))

    records = _records(capsys)
    started = _event(records, "request_started")
    completed = _event(records, "request_completed")
    assert started["method"] == "GET"
    assert started["path"] == "/characters"
    assert started["request_id"] == "req-abc"
    assert started["correlation_id"] == "corr-abc"
    assert completed["status_code"] == 200
    assert completed["duration_ms"] >= 0
    assert response.headers[REQUEST_ID_HEADER] == "req-abc"
    assert response.headers[CORRELATION_ID_HEADER] == "corr-abc"
    assert get_request_id() is None
    assert get_correlation_id() is None


def test_request_middleware_rejects_unsafe_header_ids(capsys):
    middleware = RequestLoggingMiddleware(app=lambda scope, receive, send: None)

    async def call_next(request):
        return PlainTextResponse("ok")

    request = _request([(b"x-request-id", b"not a safe id")])
    response = asyncio.run(middleware.dispatch(request, call_next))

    generated = response.headers[REQUEST_ID_HEADER]
    assert generated != "not a safe id"
    assert len(generated) == 32
    assert response.headers[CORRELATION_ID_HEADER] == generated

    started = _event(_records(capsys), "request_started")
    assert started["request_id"] == generated


def test_request_middleware_logs_failure(capsys):
    middleware = RequestLoggingMiddleware(app=lambda scope, receive, send: None)

    async def call_next(request):
        raise RuntimeError("downstream exploded")

    request = _request()
    with pytest.raises(RuntimeError, match="downstream exploded"):
        asyncio.run(middleware.dispatch(request, call_next))

    failed = _event(_records(capsys), "request_failed")
    assert failed["method"] == "GET"
    assert failed["path"] == "/characters"
    assert "RuntimeError" in failed["exception"]
    assert get_request_id() is None
    assert get_correlation_id() is None


def test_request_middleware_skips_probe_logs_but_logs_failures(capsys):
    middleware = RequestLoggingMiddleware(app=lambda scope, receive, send: None)

    async def ok(request):
        return PlainTextResponse("ok")

    asyncio.run(middleware.dispatch(_request(path="/health/live"), ok))

    out = capsys.readouterr().out
    assert "request_started" not in out
    assert "request_completed" not in out

    async def boom(request):
        raise RuntimeError("probe exploded")

    with pytest.raises(RuntimeError, match="probe exploded"):
        asyncio.run(middleware.dispatch(_request(path="/health/ready"), boom))

    out = capsys.readouterr().out
    assert "request_failed" in out
    assert get_request_id() is None
    assert get_correlation_id() is None


def test_dispatcher_binds_correlation_and_user_context(capsys):
    dispatcher = CommandDispatcher()
    seen = {}

    async def handler(envelope):
        seen["request_id"] = get_request_id()
        seen["correlation_id"] = get_correlation_id()
        seen["user_id"] = structlog.contextvars.get_contextvars().get("user_id")

    dispatcher.register(MessageType.CHARACTER_CREATE, handler)
    correlation_id = uuid.uuid4()
    envelope = create_message(
        MessageType.CHARACTER_CREATE,
        {"draft_id": "1"},
        correlation_id=correlation_id,
        headers={AUTH_USER_ID_HEADER: "user-9"},
    )

    asyncio.run(dispatcher.handle(envelope))

    assert seen["request_id"] == str(envelope.message_id)
    assert seen["correlation_id"] == str(correlation_id)
    assert seen["user_id"] == "user-9"

    handled = _event(_records(capsys), "message_handled")
    assert handled["message_type"] == "character.create.command"
    assert handled["message_id"] == str(envelope.message_id)
    assert handled["user_id"] == "user-9"
    assert handled["correlation_id"] == str(correlation_id)
    assert handled["duration_ms"] >= 0

    assert get_request_id() is None
    assert get_correlation_id() is None
    assert "user_id" not in structlog.contextvars.get_contextvars()


def test_dispatcher_generates_ids_when_envelope_has_none(capsys):
    dispatcher = CommandDispatcher()
    seen = {}

    async def handler(envelope):
        seen["request_id"] = get_request_id()
        seen["correlation_id"] = get_correlation_id()

    dispatcher.register(MessageType.CHARACTER_DELETE, handler)
    envelope = create_message(MessageType.CHARACTER_DELETE, {"draft_id": "1"})

    asyncio.run(dispatcher.handle(envelope))

    assert seen["request_id"] == str(envelope.message_id)
    assert seen["correlation_id"] == str(envelope.message_id)

    handled = _event(_records(capsys), "message_handled")
    assert handled["request_id"] == str(envelope.message_id)


def test_dispatcher_logs_message_failure(capsys):
    dispatcher = CommandDispatcher()

    async def handler(envelope):
        raise ValueError("bad draft")

    dispatcher.register(MessageType.CHARACTER_SAVE, handler)
    envelope = create_message(MessageType.CHARACTER_SAVE, {"draft_id": "1"})

    with pytest.raises(ValueError, match="bad draft"):
        asyncio.run(dispatcher.handle(envelope))

    failed = _event(_records(capsys), "message_failed")
    assert failed["message_type"] == "character.save.command"
    assert "ValueError" in failed["exception"]
    assert get_request_id() is None
    assert get_correlation_id() is None
    assert "user_id" not in structlog.contextvars.get_contextvars()
