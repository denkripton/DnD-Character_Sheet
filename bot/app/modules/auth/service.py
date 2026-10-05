from app.infrastructure.http.client import BackendApiClient
from app.modules.auth.schemas.context import AuthContext
from app.utils.exceptions import BackendAuthError

PROVIDER_TELEGRAM = "telegram"


class BotAuthService:
    def __init__(self, backend: BackendApiClient):
        self._backend = backend

    async def authenticate(self, telegram_user_id: int) -> AuthContext:
        if telegram_user_id <= 0:
            raise BackendAuthError("Telegram identity is not available")

        provider_user_id = str(telegram_user_id)
        response = await self._backend.authenticate_external(
            provider=PROVIDER_TELEGRAM,
            provider_user_id=provider_user_id,
        )

        return AuthContext(
            provider=PROVIDER_TELEGRAM,
            provider_user_id=provider_user_id,
            user_id=str(response.user.id),
            username=response.user.username,
            access_token=response.access,
        )