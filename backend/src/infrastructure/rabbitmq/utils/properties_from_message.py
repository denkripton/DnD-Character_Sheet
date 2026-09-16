from typing import Any

from src.infrastructure.rabbitmq.utils.timestamp_from_value import timestamp_from_value
from src.messaging.enums import DeliveryProperties


def properties_from_message(message: Any) -> DeliveryProperties:
    return DeliveryProperties(
        message_id=getattr(message, "message_id", None),
        correlation_id=getattr(message, "correlation_id", None),
        timestamp=timestamp_from_value(getattr(message, "timestamp", None)),
        headers=dict(getattr(message, "headers", None) or {}),
        type=getattr(message, "type", None),
    )