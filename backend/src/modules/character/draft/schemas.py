import uuid
from typing import Any

from src.utils.schemas.base_schema import BaseSchema


class CharacterDraftReadSchema(BaseSchema):
    id: uuid.UUID
    data: dict[str, Any]
    target_character_id: uuid.UUID | None = None
    modifiers: dict[str, int] | None = None
