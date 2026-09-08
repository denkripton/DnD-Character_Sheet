from pydantic import Field

from src.modules.character.proficiencies.schemas.category import ProficiencyCategory
from src.utils.schemas.base_schema import BaseSchema


class ProficiencyCreateSchema(BaseSchema):
    category: ProficiencyCategory
    name: str = Field(min_length=1, max_length=100)