from datetime import UTC, datetime
from types import SimpleNamespace
from uuid import uuid4

import pytest

from src.infrastructure.rabbitmq.serialization import serialize
from src.infrastructure.rabbitmq.utils import (
    envelope_to_properties,
    properties_from_message,
    timestamp_from_value,
    to_envelope,
)
from src.messaging.enums import DeliveryProperties
from src.messaging.messages import MessageEnvelope
from src.utils.exceptions.serialization import SerializationError


def test_envelope_to_properties_maps_envelope_fields():
    message_id = uuid4()
    correlation_id = uuid4()
    timestamp = datetime(2026, 1, 2, 3, 4, 5, tzinfo=UTC)
    envelope = MessageEnvelope(
        type="character.created",
        message_id=message_id,
        correlation_id=correlation_id,
        timestamp=timestamp,
        headers={"source": "backend"},
    )

    properties = envelope_to_properties(envelope)

    assert properties.message_id == str(message_id)
    assert properties.correlation_id == str(correlation_id)
    assert properties.timestamp == timestamp
    assert properties.headers == {"source": "backend"}
    assert properties.type == "character.created"


def test_envelope_to_properties_without_correlation_id():
    properties = envelope_to_properties(MessageEnvelope(type="ping"))

    assert properties.correlation_id is None


def test_timestamp_from_value_converts_various_inputs():
    aware = datetime(2026, 5, 6, 7, 8, 9, tzinfo=UTC)
    assert timestamp_from_value(aware) == aware
    assert timestamp_from_value(1772201289) == datetime.fromtimestamp(
        1772201289, tz=UTC
    )
    assert timestamp_from_value("2026-05-06T07:08:09+00:00") == aware
    assert timestamp_from_value(None) is None
    assert timestamp_from_value("not-a-date") is None


def test_properties_from_message_reads_ampq_style_attributes():
    message = SimpleNamespace(
        message_id=str(uuid4()),
        correlation_id=str(uuid4()),
        timestamp=1772201289,
        headers={"source": "bot"},
        type="character.updated",
    )

    properties = properties_from_message(message)

    assert properties.message_id == message.message_id
    assert properties.correlation_id == message.correlation_id
    assert properties.timestamp == datetime.fromtimestamp(
        1772201289, tz=UTC
    )
    assert properties.headers == {"source": "bot"}
    assert properties.type == "character.updated"


def test_properties_from_message_tolerates_missing_attributes():
    properties = properties_from_message(SimpleNamespace(body=b""))

    assert properties.message_id is None
    assert properties.correlation_id is None
    assert properties.timestamp is None
    assert properties.headers == {}
    assert properties.type is None


def test_to_envelope_uses_broker_properties_as_authoritative():
    message_id = uuid4()
    correlation_id = uuid4()
    timestamp = datetime(2026, 1, 1, 0, 0, 0, tzinfo=UTC)
    envelope = MessageEnvelope(
        type="original.type",
        payload={"character_id": 7},
    )
    properties = DeliveryProperties(
        message_id=str(message_id),
        correlation_id=str(correlation_id),
        timestamp=timestamp,
        headers={"source": "bot"},
        type="broker.type",
    )

    restored = to_envelope(serialize(envelope), properties)

    assert restored.message_id == message_id
    assert restored.correlation_id == correlation_id
    assert restored.timestamp == timestamp
    assert restored.type == "broker.type"
    assert restored.headers == {"source": "bot"}
    assert restored.payload == {"character_id": 7}


def test_to_envelope_merges_headers_with_body_headers():
    envelope = MessageEnvelope(type="ping", headers={"a": "1"})
    properties = DeliveryProperties(headers={"b": "2"})

    restored = to_envelope(serialize(envelope), properties)

    assert restored.headers == {"a": "1", "b": "2"}


def test_to_envelope_rejects_malformed_body():
    with pytest.raises(SerializationError):
        to_envelope(b"not-json", DeliveryProperties())