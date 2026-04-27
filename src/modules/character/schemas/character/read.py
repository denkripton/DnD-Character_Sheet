from pydantic import Field

from src.modules.character.schemas.character.creation import CharacterCreateSchema


class CharacterReadSchema(CharacterCreateSchema):
    creator: dict[str, str] = Field(example={"name": "John Doe"})