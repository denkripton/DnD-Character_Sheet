from uuid import UUID


def coerce_identifier(value):
    try:
        return UUID(str(value))
    except (TypeError, ValueError):
        return value
