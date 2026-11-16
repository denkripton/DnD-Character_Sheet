import uuid

from pydantic import Field
from src.utils.schemas.base_schema import BaseSchema


class BackstoryReadSchema(BaseSchema):
    backstory: str = Field(default="")
    id: uuid.UUID
