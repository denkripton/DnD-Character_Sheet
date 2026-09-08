from pydantic import Field

from src.utils.schemas.base_schema import BaseSchema


class FeatureCreateSchema(BaseSchema):
    name: str = Field(min_length=1, max_length=100)
    description: str = Field(default="", max_length=10000)