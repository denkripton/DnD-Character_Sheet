import uuid

from app.schemas.base import BaseSchema


class ExternalAuthUser(BaseSchema):
    id: uuid.UUID
    username: str


class ExternalAuthResponse(BaseSchema):
    access: str
    refresh: str
    user: ExternalAuthUser
