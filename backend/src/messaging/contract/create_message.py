from typing import Any
from uuid import UUID

from src.messaging.enums import MessageType
from src.messaging.messages import MessageEnvelope


def create_message(
    message_type: MessageType,
    payload: Any = None,
    *,
    correlation_id: UUID | None = None,
    headers: dict[str, str] | None = None,
) -> MessageEnvelope:
    return MessageEnvelope(
        type=message_type.value,
        correlation_id=correlation_id,
        headers=dict(headers or {}),
        payload=payload if payload is not None else {},
    )
