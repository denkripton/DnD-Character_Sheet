import asyncio
from datetime import UTC, datetime, timedelta
from unittest.mock import AsyncMock
from uuid import uuid4

import pytest
from src.messaging.enums import MessageType
from src.messaging.enums.constants.command_headers import (
    AUTH_PROVIDER_HEADER,
    AUTH_PROVIDER_USER_ID_HEADER,
    AUTH_USER_ID_HEADER,
    COMMAND_SIGNATURE_HEADER,
)
from src.messaging.enums.constants.retry import RETRY_COUNT_HEADER
from src.messaging.messages import MessageEnvelope
from src.messaging.security import (
    require_identity_headers,
    sign_command,
    verify_command,
)
from src.utils.exceptions import MessageAuthenticationError

SECRET = "shared-secret"


def _envelope(**overrides) -> MessageEnvelope:
    headers = {
        AUTH_PROVIDER_HEADER: "telegram",
        AUTH_PROVIDER_USER_ID_HEADER: "7",
        AUTH_USER_ID_HEADER: "user-1",
    }
    return MessageEnvelope(
        type=MessageType.CHARACTER_GENERATE.value,
        payload={"user_id": 7},
        headers=headers,
        **overrides,
    )


def test_sign_then_verify_round_trip():
    envelope = _envelope()
    signed = sign_command(envelope, SECRET)

    assert signed is not envelope
    assert COMMAND_SIGNATURE_HEADER in signed.headers

    verify_command(signed, SECRET, max_age_seconds=300)


def test_verify_tolerates_amqp_second_precision_timestamp():
    envelope = _envelope(timestamp=datetime.now(UTC))
    signed = sign_command(envelope, SECRET)
    delivered = MessageEnvelope(
        type=signed.type,
        message_id=signed.message_id,
        correlation_id=signed.correlation_id,
        timestamp=signed.timestamp.replace(microsecond=0),
        headers=dict(signed.headers),
        payload=signed.payload,
    )

    verify_command(delivered, SECRET, max_age_seconds=300)


def test_verify_rejects_tampered_payload():
    envelope = _envelope()
    signed = sign_command(envelope, SECRET)
    tampered = signed.model_copy(update={"payload": {"user_id": 999}})

    with pytest.raises(MessageAuthenticationError):
        verify_command(tampered, SECRET)


def test_verify_rejects_tampered_header():
    envelope = _envelope()
    signed = sign_command(envelope, SECRET)
    tampered = signed.model_copy(
        update={"headers": {**signed.headers, AUTH_PROVIDER_USER_ID_HEADER: "99"}}
    )

    with pytest.raises(MessageAuthenticationError):
        verify_command(tampered, SECRET)


def test_verify_rejects_tampered_message_id():
    envelope = _envelope()
    signed = sign_command(envelope, SECRET)
    tampered = signed.model_copy(update={"message_id": uuid4()})

    with pytest.raises(MessageAuthenticationError):
        verify_command(tampered, SECRET)


def test_verify_rejects_wrong_secret():
    envelope = _envelope()
    signed = sign_command(envelope, "other-secret")

    with pytest.raises(MessageAuthenticationError):
        verify_command(signed, SECRET)


def test_verify_rejects_missing_signature():
    with pytest.raises(MessageAuthenticationError):
        verify_command(_envelope(), SECRET)


def test_verify_rejects_stale_timestamp():
    envelope = _envelope(
        timestamp=datetime.now(UTC) - timedelta(seconds=400),
    )
    signed = sign_command(envelope, SECRET)

    with pytest.raises(MessageAuthenticationError):
        verify_command(signed, SECRET, max_age_seconds=300)


def test_verify_rejects_future_timestamp():
    envelope = _envelope(
        timestamp=datetime.now(UTC) + timedelta(seconds=400),
    )
    signed = sign_command(envelope, SECRET)

    with pytest.raises(MessageAuthenticationError):
        verify_command(signed, SECRET, max_age_seconds=300)


def test_retry_header_does_not_invalidate_signature():
    envelope = _envelope()
    signed = sign_command(envelope, SECRET)
    retried = signed.model_copy(
        update={"headers": {**signed.headers, RETRY_COUNT_HEADER: "2"}}
    )

    verify_command(retried, SECRET, max_age_seconds=300)


def test_sign_requires_secret():
    with pytest.raises(MessageAuthenticationError):
        sign_command(_envelope(), "")


def test_verify_requires_configured_secret():
    envelope = sign_command(_envelope(), SECRET)
    with pytest.raises(MessageAuthenticationError):
        verify_command(envelope, "", max_age_seconds=300)


def test_require_identity_headers_returns_mapping():
    identity = require_identity_headers(_envelope())
    assert identity[AUTH_PROVIDER_HEADER] == "telegram"
    assert identity[AUTH_PROVIDER_USER_ID_HEADER] == "7"
    assert identity[AUTH_USER_ID_HEADER] == "user-1"


def test_require_identity_headers_rejects_missing():
    with pytest.raises(MessageAuthenticationError):
        require_identity_headers(MessageEnvelope(type="ping"))


def test_dispatcher_accepts_signed_command_with_identity():
    from src.modules.commands.dispatcher_factory import build_bot_command_dispatcher

    producer = AsyncMock()
    dispatcher = build_bot_command_dispatcher(
        producer, secret=SECRET, max_age_seconds=300
    )
    envelope = sign_command(_envelope(), SECRET)

    asyncio.run(dispatcher.handle(envelope))

    producer.publish.assert_awaited_once()


def test_dispatcher_rejects_unsigned_command():
    from src.modules.commands.dispatcher_factory import build_bot_command_dispatcher

    producer = AsyncMock()
    dispatcher = build_bot_command_dispatcher(
        producer, secret=SECRET, max_age_seconds=300
    )

    with pytest.raises(MessageAuthenticationError):
        asyncio.run(dispatcher.handle(_envelope()))

    producer.publish.assert_not_awaited()


def test_dispatcher_rejects_signed_command_without_identity():
    from src.modules.commands.dispatcher_factory import build_bot_command_dispatcher

    producer = AsyncMock()
    dispatcher = build_bot_command_dispatcher(
        producer, secret=SECRET, max_age_seconds=300
    )
    envelope = _envelope()
    unsigned_identity = envelope.model_copy(update={"headers": {}})
    signed = sign_command(unsigned_identity, SECRET)

    with pytest.raises(MessageAuthenticationError):
        asyncio.run(dispatcher.handle(signed))

    producer.publish.assert_not_awaited()


def test_dispatcher_without_secret_does_not_enforce_auth():
    from src.modules.commands.dispatcher_factory import build_bot_command_dispatcher

    producer = AsyncMock()
    dispatcher = build_bot_command_dispatcher(producer)

    asyncio.run(dispatcher.handle(_envelope()))

    producer.publish.assert_awaited_once()