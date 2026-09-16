from datetime import UTC, datetime
from typing import Any
from uuid import UUID, uuid4

from pydantic import BaseModel, Field


class MessageEnvelope(BaseModel):
    type: str
    message_id: UUID = Field(default_factory=uuid4)
    correlation_id: UUID | None = None
    timestamp: datetime = Field(default_factory=lambda: datetime.now(UTC))
    headers: dict[str, str] = Field(default_factory=dict)
    payload: Any = Field(default_factory=dict)