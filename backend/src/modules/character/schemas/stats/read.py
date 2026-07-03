from pydantic import Field

from src.modules.character.schemas.stats.create import StatsCreateSchema


class StatsReadSchema(StatsCreateSchema):
    strength: int = Field(ge=-1, le=4)
    dexterity: int = Field(ge=-1, le=4)
    constitution: int = Field(ge=-1, le=4)
    intelligence: int = Field(ge=-1, le=4)
    wisdom: int = Field(ge=-1, le=4)
    charisma: int = Field(ge=-1, le=4)