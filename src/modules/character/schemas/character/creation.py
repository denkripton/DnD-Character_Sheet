from typing import Optional

from pydantic import Field

from src.utils.schemas.base_schema import BaseSchema


class CharacterCreateSchema(BaseSchema):
    name: Optional[str] = Field(max_length=100, examples=["John the Great"])
    spec_class: str = Field(max_length=20, examples=["Figher"])
    kind: str = Field(max_length=20, examples=["Human"])
