import logging
import sys

import structlog
from structlog.stdlib import ProcessorFormatter

from src.utils.logging.sanitize import sanitize_processor


class _StdoutHandler(logging.StreamHandler):
    def __init__(self) -> None:
        super().__init__(None)

    @property
    def stream(self):
        return sys.stdout

    @stream.setter
    def stream(self, value) -> None:
        self._stream = value


def _add_service_fields(service: str, environment: str):
    def processor(logger, method_name, event_dict: dict) -> dict:
        event_dict.setdefault("service", service)
        event_dict.setdefault("environment", environment)
        return event_dict

    return processor


def _shared_processors(service: str, environment: str) -> list:
    return [
        structlog.contextvars.merge_contextvars,
        structlog.stdlib.add_log_level,
        structlog.stdlib.add_logger_name,
        structlog.processors.TimeStamper(fmt="iso", utc=True),
        _add_service_fields(service, environment),
        sanitize_processor,
    ]


def _render_processors(json_output: bool) -> list:
    processors = [
        ProcessorFormatter.remove_processors_meta,
        structlog.processors.StackInfoRenderer(),
        structlog.processors.format_exc_info,
        sanitize_processor,
    ]
    if json_output:
        processors.append(structlog.processors.JSONRenderer(ensure_ascii=False))
    else:
        processors.append(structlog.dev.ConsoleRenderer(colors=False))
    return processors


def configure_logging(
    level: str = "INFO",
    *,
    service: str,
    environment: str,
    json_output: bool = True,
) -> None:
    numeric_level = getattr(logging, str(level).upper(), logging.INFO)
    shared = _shared_processors(service, environment)
    structlog.configure(
        processors=[
            *shared,
            structlog.processors.StackInfoRenderer(),
            structlog.processors.format_exc_info,
            ProcessorFormatter.wrap_for_formatter,
        ],
        logger_factory=structlog.stdlib.LoggerFactory(),
        wrapper_class=structlog.stdlib.BoundLogger,
        cache_logger_on_first_use=True,
    )
    formatter = ProcessorFormatter(
        foreign_pre_chain=shared,
        processors=_render_processors(json_output),
    )
    handler = _StdoutHandler()
    handler.setFormatter(formatter)
    handler.setLevel(numeric_level)
    root = logging.getLogger()
    for existing in list(root.handlers):
        root.removeHandler(existing)
    root.addHandler(handler)
    root.setLevel(numeric_level)
