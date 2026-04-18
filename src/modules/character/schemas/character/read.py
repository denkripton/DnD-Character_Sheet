from pydantic import Field

from src.modules.character.schemas.character.creation import CharacterCreateSchema


class CharacterRead(CharacterCreateSchema):
    creator: dict[str, str] = Field(example={"name": "John Doe"})