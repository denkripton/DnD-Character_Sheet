import uuid
from typing import Optional

from src.modules.character.schemas.character.creation import CharacterCreateSchema
from src.modules.character.schemas.stats.read import StatsReadSchema
from src.modules.character.schemas.stats.read_modifiers import ModifiersReadSchema

class CharacterReadSchema(CharacterCreateSchema):
    stats: Optional[StatsReadSchema]
    modifiers: Optional[ModifiersReadSchema] = None
    id: uuid.UUID
