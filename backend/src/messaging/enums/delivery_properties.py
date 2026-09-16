from dataclasses import dataclass, field
from datetime import datetime


@dataclass(frozen=True)
class DeliveryProperties:
    message_id: str | None = None
    correlation_id: str | None = None
    timestamp: datetime | None = None
    headers: dict[str, str] = field(default_factory=dict)
    type: str | None = None