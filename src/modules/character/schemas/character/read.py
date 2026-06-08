import uuid

from src.modules.character.schemas.character.creation import CharacterCreateSchema


class CharacterReadSchema(CharacterCreateSchema):
    id: uuid.UUID
