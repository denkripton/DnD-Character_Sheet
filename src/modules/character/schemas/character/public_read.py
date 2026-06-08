import uuid

from pydantic import Field

from src.modules.character.schemas.character.read import CharacterReadSchema


class PublicCharacterReadSchema(CharacterReadSchema):
    creator: dict[str, str] = Field(example={"name": "John Doe"})
