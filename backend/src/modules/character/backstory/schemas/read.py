import uuid

from pydantic import Field

from src.utils.schemas.base_schema import BaseSchema


class BackstoryCreateSchema(BaseSchema):
    backstory: str = Field(..., min_length=1, max_length=10000)


class BackstoryReadSchema(BaseSchema):
    backstory: str = Field(default="")
    id: uuid.UUID