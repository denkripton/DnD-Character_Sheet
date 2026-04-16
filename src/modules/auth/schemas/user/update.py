from pydantic import Field

from src.utils.schemas.base_schema import BaseSchema


class UserUpdateSchema(BaseSchema):
    username: str = Field(max_length=20, examples=["John Doe"])
    password: str = Field(min_length=8, max_length=64, examples=["som@Th1ng"])
