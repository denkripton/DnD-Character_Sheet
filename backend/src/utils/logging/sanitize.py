import re
from collections.abc import Mapping

REDACTED = "[REDACTED]"

SENSITIVE_KEY_PARTS = (
    "password",
    "passwd",
    "secret",
    "token",
    "api_key",
    "apikey",
    "authorization",
    "cookie",
    "jwt",
    "bearer",
    "private_key",
)

_URL_CREDENTIALS_PATTERN = re.compile(
    r"(?P<scheme>[a-z][a-z0-9+.-]*://)[^/\s:@]*:[^/\s@]+@",
    re.IGNORECASE,
)
_INLINE_SECRET_PATTERN = re.compile(
    r"\b(password|passwd|secret|token|api[_-]?key|authorization|jwt)\b\s*[=:]\s*[^\s,;\"']+",
    re.IGNORECASE,
)
_SECRET_VALUE_PATTERN = re.compile(
    r"Bearer\s+\S+"
    r"|eyJ[\w-]+\.[\w-]+\.[\w-]+"
    r"|-----BEGIN [A-Z ]*PRIVATE KEY-----",
    re.IGNORECASE,
)


def is_sensitive_key(key: object) -> bool:
    normalized = re.sub(r"[^a-z0-9]", "", str(key).lower())
    return any(part.replace("_", "") in normalized for part in SENSITIVE_KEY_PARTS)


def _scrub_value(value: object) -> object:
    if not isinstance(value, str):
        return value
    scrubbed = _SECRET_VALUE_PATTERN.sub(REDACTED, value)
    scrubbed = _URL_CREDENTIALS_PATTERN.sub(
        lambda match: f"{match.group('scheme')}{REDACTED}@",
        scrubbed,
    )
    return _INLINE_SECRET_PATTERN.sub(r"\1=[REDACTED]", scrubbed)


def sanitize_event_dict(event_dict: dict) -> dict:
    cleaned: dict = {}
    for key, value in event_dict.items():
        if is_sensitive_key(key):
            cleaned[key] = REDACTED
        elif isinstance(value, Mapping):
            cleaned[key] = sanitize_event_dict(dict(value))
        elif isinstance(value, (list, tuple)):
            scrubbed = [
                sanitize_event_dict(dict(item)) if isinstance(item, Mapping) else _scrub_value(item)
                for item in value
            ]
            cleaned[key] = type(value)(scrubbed)
        else:
            cleaned[key] = _scrub_value(value)
    return cleaned


def sanitize_processor(logger, method_name, event_dict: dict) -> dict:
    return sanitize_event_dict(event_dict)
