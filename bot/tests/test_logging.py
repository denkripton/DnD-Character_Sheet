import json

import structlog
from app.utils.logging import configure_logging


def _records(capsys) -> list[dict]:
    out = capsys.readouterr().out
    return [json.loads(line) for line in out.splitlines() if line.strip()]


def test_configure_logging_marks_structlog_configured():
    configure_logging("INFO", service="bot", environment="test")
    assert structlog.is_configured()


def test_configure_logging_accepts_unknown_level():
    configure_logging("NOT-A-LEVEL", service="bot", environment="test")
    assert structlog.is_configured()


def test_configure_logging_emits_json_with_service_fields(capsys):
    configure_logging("INFO", service="bot", environment="test", json_output=True)
    structlog.get_logger("app.test").info("bot_event", user_id=7)

    record = next(
        line for line in map(json.loads, capsys.readouterr().out.splitlines()) if line
    )
    assert record["event"] == "bot_event"
    assert record["user_id"] == 7
    assert record["level"] == "info"
    assert record["logger"] == "app.test"
    assert record["service"] == "bot"
    assert record["environment"] == "test"
    assert record["timestamp"]


def test_configure_logging_redacts_sensitive_values(capsys):
    configure_logging("INFO", service="bot", environment="test", json_output=True)
    structlog.get_logger("app.test").info(
        "secret_event",
        token="abc123",
        password="hunter2",
        note="Bearer abc.def",
        nested={"api_key": "k-1", "safe": "keep"},
    )

    record = _records(capsys)[-1]
    assert record["token"] == "[REDACTED]"
    assert record["password"] == "[REDACTED]"
    assert record["note"] == "[REDACTED]"
    assert record["nested"]["api_key"] == "[REDACTED]"
    assert record["nested"]["safe"] == "keep"
