import json
from uuid import uuid4

import pytest

from src.infrastructure.rabbitmq.serialization import deserialize, serialize
from src.messaging.messages import MessageEnvelope
from src.utils.exceptions.serialization import SerializationError


def test_serialize_round_trip_preserves_all_fields():
    envelope = MessageEnvelope(
        type="character.updated",
        message_id=uuid4(),
        correlation_id=uuid4(),
        headers={"source": "bot", "version": "1"},
        payload={"character_id": 42, "name": "Aragorn"},
    )

    restored = deserialize(serialize(envelope))

    assert restored == envelope


def test_serialize_produces_utf8_json_document():
    envelope = MessageEnvelope(type="character.updated", payload={"x": 1})

    document = json.loads(serialize(envelope).decode("utf-8"))

    assert set(document) == {
        "type",
        "message_id",
        "correlation_id",
        "timestamp",
        "headers",
        "payload",
    }
    assert document["type"] == "character.updated"
    assert document["headers"] == {}
    assert document["payload"] == {"x": 1}


def test_serialize_generates_default_identifiers():
    envelope = MessageEnvelope(type="character.updated")

    restored = deserialize(serialize(envelope))

    assert restored.message_id is not None
    assert restored.timestamp is not None


def test_deserialize_rejects_malformed_json():
    with pytest.raises(SerializationError):
        deserialize(b"this is not json")


def test_deserialize_rejects_json_that_is_not_an_envelope():
    with pytest.raises(SerializationError):
        deserialize(b'{"payload": {"x": 1}}')