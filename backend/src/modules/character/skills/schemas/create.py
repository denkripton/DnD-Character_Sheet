from pydantic import Field

from src.modules.character.skills.schemas.ability import SkillAbility
from src.utils.schemas.base_schema import BaseSchema


class SkillCreateSchema(BaseSchema):
    name: str = Field(min_length=1, max_length=50)
    ability: SkillAbility
    proficiency: bool = False