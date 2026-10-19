from pydantic import Field

from src.utils.schemas.base_schema import BaseSchema


class TelegramMiniAppAuthRequest(BaseSchema):
    init_data: str = Field(min_length=1, max_length=8192)
