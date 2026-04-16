from src.utils.schemas.base_schema import BaseSchema


class AuthReadSchema(BaseSchema):
    access: str
    refresh: str
