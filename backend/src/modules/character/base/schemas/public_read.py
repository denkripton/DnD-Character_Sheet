from pydantic import Field

from src.modules.character.base.schemas.read import CharacterReadSchema


class PublicCharacterReadSchema(CharacterReadSchema):
    creator: dict[str, str] = Field(
        json_schema_extra={"example": {"name": "John Doe"}},
    )