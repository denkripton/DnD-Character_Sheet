from pydantic import EmailStr, Field

from src.utils.schemas.base_schema import BaseSchema


class UserLoginSchema(BaseSchema):
    email: EmailStr = Field(max_length=50, examples=["johndoe@gmail.com"])
    password: str = Field(min_length=8, max_length=64, examples=["som@Th1ng"])
