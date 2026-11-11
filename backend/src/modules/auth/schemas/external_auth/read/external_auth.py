from src.modules.auth.schemas.external_auth.read.external_user import ExternalUserRead
from src.utils.schemas.base_schema import BaseSchema


class ExternalAuthSchema(BaseSchema):
    access: str
    refresh: str
    user: ExternalUserRead
