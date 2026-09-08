from typing import Optional

from pydantic import Field

from src.utils.schemas.base_schema import BaseSchema


class CharacterUpdateSchema(BaseSchema):
    name: Optional[str] = Field(default=None, max_length=100)
    spec_class: Optional[str] = Field(default=None, max_length=20)
    kind: Optional[str] = Field(default=None, max_length=20)
    alignment: Optional[str] = Field(default=None, max_length=30)
    background: Optional[str] = Field(default=None, max_length=50)
    experience_points: Optional[int] = Field(default=None, ge=0, le=1000000000)
    level: Optional[int] = Field(default=None, ge=1, le=20)