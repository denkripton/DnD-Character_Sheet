from datetime import datetime
from typing import NamedTuple

from src.messaging.enums.constants import EMPTY_HEADERS


class DeliveryProperties(NamedTuple):
    message_id: str | None = None
    correlation_id: str | None = None
    timestamp: datetime | None = None
    headers: dict[str, str] = EMPTY_HEADERS
    type: str | None = None