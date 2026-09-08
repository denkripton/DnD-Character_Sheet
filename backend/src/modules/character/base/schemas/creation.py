from typing import Optional

from pydantic import Field

from src.utils.schemas.base_schema import BaseSchema


class CharacterCreateSchema(BaseSchema):
    name: Optional[str] = Field(max_length=100, examples=["John the Great"])
    spec_class: str = Field(max_length=20, examples=["Figher"])
    kind: str = Field(max_length=20, examples=["Human"])
    alignment: Optional[str] = Field(
        default=None, max_length=30, examples=["Lawful Good"]
    )
    background: Optional[str] = Field(
        default=None, max_length=50, examples=["Soldier"]
    )
    experience_points: Optional[int] = Field(default=0, ge=0, le=1000000000)
    level: Optional[int] = Field(default=1, ge=1, le=20, examples=[1, 5])