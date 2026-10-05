import hashlib
import hmac
import json
from datetime import UTC, datetime

from src.messaging.enums.constants.command_headers import (
    AUTH_PROVIDER_HEADER,
    AUTH_PROVIDER_USER_ID_HEADER,
    AUTH_USER_ID_HEADER,
    COMMAND_SIGNATURE_HEADER,
)
from src.messaging.enums.constants.retry import RETRY_COUNT_HEADER
from src.messaging.messages import MessageEnvelope
from src.utils.exceptions import MessageAuthenticationError

EXCLUDED_FROM_SIGNATURE = frozenset({COMMAND_SIGNATURE_HEADER, RETRY_COUNT_HEADER})
IDENTITY_HEADERS = (
    AUTH_PROVIDER_HEADER,
    AUTH_PROVIDER_USER_ID_HEADER,
    AUTH_USER_ID_HEADER,
)


def _json_string(value) -> str:
    return json.dumps(
        value,
        sort_keys=True,
        separators=(",", ":"),
        ensure_ascii=False,
        default=str,
    )


def _canonical_timestamp(envelope: MessageEnvelope) -> str:
    timestamp = envelope.timestamp
    if timestamp.tzinfo is None:
        timestamp = timestamp.replace(tzinfo=UTC)
    return timestamp.replace(microsecond=0).isoformat()


def _canonical_string(envelope: MessageEnvelope) -> str:
    headers = {
        key: value
        for key, value in envelope.headers.items()
        if key not in EXCLUDED_FROM_SIGNATURE
    }
    return "|".join(
        [
            envelope.type,
            str(envelope.message_id),
            _canonical_timestamp(envelope),
            _json_string(envelope.payload),
            _json_string(headers),
        ]
    )


def _compute_signature(envelope: MessageEnvelope, secret: str) -> str:
    if not secret:
        raise MessageAuthenticationError("Command signing is not configured")
    message = _canonical_string(envelope).encode("utf-8")
    return hmac.new(secret.encode("utf-8"), message, hashlib.sha256).hexdigest()


def sign_command(envelope: MessageEnvelope, secret: str) -> MessageEnvelope:
    digest = _compute_signature(envelope, secret)
    return envelope.model_copy(
        update={"headers": {**envelope.headers, COMMAND_SIGNATURE_HEADER: digest}}
    )


def verify_command(
    envelope: MessageEnvelope,
    secret: str,
    max_age_seconds: int = 300,
) -> None:
    if not secret:
        raise MessageAuthenticationError("Command verification is not configured")

    provided = envelope.headers.get(COMMAND_SIGNATURE_HEADER)
    if not provided:
        raise MessageAuthenticationError("Command is missing signature")

    expected = _compute_signature(envelope, secret)
    if not hmac.compare_digest(provided, expected):
        raise MessageAuthenticationError("Command signature is invalid")

    timestamp = envelope.timestamp
    if timestamp.tzinfo is None:
        timestamp = timestamp.replace(tzinfo=UTC)
    age_seconds = abs((datetime.now(UTC) - timestamp).total_seconds())
    if age_seconds > max_age_seconds:
        raise MessageAuthenticationError("Command has expired")


def require_identity_headers(envelope: MessageEnvelope) -> dict[str, str]:
    missing = [
        header for header in IDENTITY_HEADERS if not envelope.headers.get(header)
    ]
    if missing:
        raise MessageAuthenticationError(
            "Command is missing identity headers: " + ", ".join(missing)
        )
    return {header: envelope.headers[header] for header in IDENTITY_HEADERS}