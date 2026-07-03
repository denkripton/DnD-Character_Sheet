import uuid
from typing import Optional

from src.modules.character.schemas.character.creation import CharacterCreateSchema
from src.modules.character.schemas.stats.read import StatsReadSchema

class CharacterReadSchema(CharacterCreateSchema):
    stats: Optional[StatsReadSchema]
    id: uuid.UUID
