import re

from pydantic import field_validator, EmailStr, Field

from src.utils.schemas.base_schema import BaseSchema


class UserCreateSchema(BaseSchema):
    username: str = Field(max_length=20, examples=["John Doe"])
    email: EmailStr = Field(max_length=50, examples=["johndoe@gmail.com"])
    password: str = Field(min_length=8, max_length=64, examples=["som@Th1ng"])

    @field_validator("password")
    def validate_password(cls, password: str) -> str:
        if not re.fullmatch(
            r"^(?=.*[a-z])(?=.*[A-Z])(?=.*\d)(?=.*[@$!%*?&])[A-Za-z\d@$!%*?&]{8,64}$",
            password,
        ):
            raise ValueError(
                """Password is invalid. It must contain at least: one lowercase letter, one upper case letter, one digit, one special character. Length: 8-64"""
            )
        return password
