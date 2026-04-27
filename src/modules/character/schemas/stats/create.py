from pydantic import Field

from src.utils.schemas.base_schema import BaseSchema


class CreateStatsSchema(BaseSchema):
    strength: int = Field(ge=8, le=17, default=8)
    dexterity: int = Field(ge=8, le=17, default=8)
    constitution: int = Field(ge=8, le=17, default=8)
    intelligence: int = Field(ge=8, le=17, default=8)
    wisdom: int = Field(ge=8, le=17, default=8)
    charisma: int = Field(ge=8, le=17, default=8)   