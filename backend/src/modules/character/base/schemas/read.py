import uuid

from src.modules.character.base.schemas.creation import CharacterCreateSchema


class CharacterReadSchema(CharacterCreateSchema):
    id: uuid.UUID