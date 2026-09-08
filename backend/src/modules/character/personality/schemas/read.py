import uuid

from pydantic import Field

from src.utils.schemas.base_schema import BaseSchema


class PersonalityCreateSchema(BaseSchema):
    personality_traits: str = Field(default="", max_length=10000)
    ideals: str = Field(default="", max_length=10000)
    bonds: str = Field(default="", max_length=10000)
    flaws: str = Field(default="", max_length=10000)


class PersonalityReadSchema(PersonalityCreateSchema):
    id: uuid.UUID