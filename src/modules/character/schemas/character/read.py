import uuid

from pydantic import Field

from src.modules.character.schemas.character.creation import CharacterCreateSchema


class CharacterReadSchema(CharacterCreateSchema):
    id: uuid.UUID
    creator: dict[str, str] = Field(example={"name": "John Doe"})