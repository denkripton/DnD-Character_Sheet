import logging
import sys

import structlog


def configure_logging(level: str) -> None:
    level_value = getattr(logging, level.upper(), logging.INFO)
    logging.basicConfig(level=level_value, format="%(message)s", stream=sys.stdout, force=True)
    structlog.configure(
        processors=[
            structlog.contextvars.merge_contextvars,
            structlog.processors.add_log_level,
            structlog.processors.TimeStamper(fmt="iso"),
            structlog.processors.StackInfoRenderer(),
            structlog.processors.format_exc_info,
            structlog.dev.ConsoleRenderer(),
        ],
        wrapper_class=structlog.make_filtering_bound_logger(level_value),
        logger_factory=structlog.stdlib.LoggerFactory(),
        cache_logger_on_first_use=True,
    )