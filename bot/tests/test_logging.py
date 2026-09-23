import structlog
from app.utils.logging import configure_logging


def test_configure_logging_marks_structlog_configured():
    configure_logging("INFO")
    assert structlog.is_configured()


def test_configure_logging_accepts_unknown_level():
    configure_logging("NOT-A-LEVEL")
    assert structlog.is_configured()