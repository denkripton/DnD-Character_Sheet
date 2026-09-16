from src.messaging.messages import MessageEnvelope
from src.utils.exceptions.serialization import SerializationError


def serialize(envelope: MessageEnvelope) -> bytes:
    return envelope.model_dump_json().encode("utf-8")


def deserialize(body: bytes) -> MessageEnvelope:
    try:
        return MessageEnvelope.model_validate_json(body)
    except ValueError as exc:
        raise SerializationError("Message body is not a valid envelope") from exc