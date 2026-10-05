import uuid

from src.utils.schemas.base_schema import BaseSchema


class ExternalUserRead(BaseSchema):
    id: uuid.UUID
    username: str


class ExternalAuthSchema(BaseSchema):
    access: str
    refresh: str
    user: ExternalUserRead