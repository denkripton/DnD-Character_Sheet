from src.modules.auth.schemas.external_auth.read import ExternalUserRead
from src.utils.schemas.base_schema import BaseSchema


class TelegramMiniAppAuthResponse(BaseSchema):
    access: str
    user: ExternalUserRead
