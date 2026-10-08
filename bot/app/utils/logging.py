from src.utils.logging import configure_logging as configure_structlog


def configure_logging(
    level: str,
    *,
    service: str,
    environment: str,
    json_output: bool = True,
) -> None:
    configure_structlog(
        level,
        service=service,
        environment=environment,
        json_output=json_output,
    )
