from src.infrastructure.rabbitmq.serialization import deserialize
from src.infrastructure.rabbitmq.utils.uuid_or_none import _uuid_or_none
from src.messaging.enums import DeliveryProperties
from src.messaging.messages import MessageEnvelope


def to_envelope(body: bytes, properties: DeliveryProperties) -> MessageEnvelope:
    envelope = deserialize(body)
    message_id = _uuid_or_none(properties.message_id)
    correlation_id = _uuid_or_none(properties.correlation_id)
    if message_id is not None:
        envelope.message_id = message_id
    if correlation_id is not None:
        envelope.correlation_id = correlation_id
    if properties.timestamp is not None:
        envelope.timestamp = properties.timestamp
    if properties.type:
        envelope.type = properties.type
    if properties.headers:
        envelope.headers.update(properties.headers)
    return envelope