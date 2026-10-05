import aiohttp

from app.config import BotConfig
from app.infrastructure.http.dto import ExternalAuthResponse
from app.utils.exceptions import BackendAuthError

AUTH_BOT_SECRET_HEADER = "X-Bot-Secret"
EXTERNAL_AUTH_PATH = "/users/auth/external"


class BackendApiClient:
    def __init__(
        self,
        config: BotConfig,
        session: aiohttp.ClientSession | None = None,
    ):
        self._config = config
        self._session = session

    @property
    def base_url(self) -> str:
        return self._config.BACKEND_BASE_URL.rstrip("/")

    async def authenticate_external(
        self,
        provider: str,
        provider_user_id: str,
    ) -> ExternalAuthResponse:
        secret = self._config.BOT_API_SECRET
        if not secret:
            raise BackendAuthError("BOT_API_SECRET is not configured")

        owns_session = self._session is None
        session = self._session or aiohttp.ClientSession()
        try:
            async with session.post(
                f"{self.base_url}{EXTERNAL_AUTH_PATH}",
                json={
                    "provider": provider,
                    "provider_user_id": provider_user_id,
                },
                headers={AUTH_BOT_SECRET_HEADER: secret},
            ) as response:
                if response.status >= 400:
                    raise BackendAuthError(
                        f"Backend authentication failed with status {response.status}"
                    )
                try:
                    data = await response.json()
                    return ExternalAuthResponse.model_validate(data)
                except (ValueError, aiohttp.ClientError) as exc:
                    raise BackendAuthError(
                        "Backend returned an invalid auth response"
                    ) from exc
        except aiohttp.ClientError as exc:
            raise BackendAuthError("Backend is unreachable") from exc
        finally:
            if owns_session:
                await session.close()