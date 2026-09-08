from pydantic import Field
from src.utils.schemas.base_schema import BaseSchema

class ModifiersReadSchema(BaseSchema):
    strength: int = Field(ge=-5, le=10)
    dexterity: int = Field(ge=-5, le=10)
    constitution: int = Field(ge=-5, le=10)
    intelligence: int = Field(ge=-5, le=10)
    wisdom: int = Field(ge=-5, le=10)
    charisma: int = Field(ge=-5, le=10)