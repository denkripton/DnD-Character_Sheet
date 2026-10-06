import uuid
from typing import Any

from src.utils.schemas.base_schema import BaseSchema


class CharacterDraftReadSchema(BaseSchema):
    id: uuid.UUID
    data: dict[str, Any]
