import uuid

from pydantic import Field

from src.modules.character.backstory.schemas.create import BackstoryCreateSchema
from src.utils.schemas.base_schema import BaseSchema

__all__ = [
    "BackstoryCreateSchema",
    "BackstoryReadSchema",
    "BaseSchema",
    "Field",
    "uuid",
]


class BackstoryReadSchema(BaseSchema):
    backstory: str = Field(default="")
    id: uuid.UUID
