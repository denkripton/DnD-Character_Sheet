import uuid

from app.utils.schemas.base_schema import BaseSchema


class ExternalAuthUser(BaseSchema):
    id: uuid.UUID
    username: str


class ExternalAuthResponse(BaseSchema):
    access: str
    refresh: str
    user: ExternalAuthUser