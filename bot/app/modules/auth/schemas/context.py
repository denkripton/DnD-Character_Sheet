from app.schemas.base import BaseSchema


class AuthContext(BaseSchema):
    provider: str
    provider_user_id: str
    user_id: str
    username: str
    access_token: str
