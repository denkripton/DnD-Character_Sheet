from src.messaging.enums import DeliveryProperties
from src.messaging.messages import MessageEnvelope


def envelope_to_properties(envelope: MessageEnvelope) -> DeliveryProperties:
    return DeliveryProperties(
        message_id=str(envelope.message_id),
        correlation_id=(
            str(envelope.correlation_id) if envelope.correlation_id is not None else None
        ),
        timestamp=envelope.timestamp,
        headers=dict(envelope.headers),
        type=envelope.type,
    )