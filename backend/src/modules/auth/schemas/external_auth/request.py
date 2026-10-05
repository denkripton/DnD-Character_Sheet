from src.utils.schemas.base_schema import BaseSchema


class ExternalAuthRequestSchema(BaseSchema):
    provider: str
    provider_user_id: str