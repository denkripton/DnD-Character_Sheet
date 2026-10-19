import hmac
import secrets
import uuid

from sqlalchemy.exc import IntegrityError

from src.config import settings
from src.databases.unit_of_work import UnitOfWork
from src.modules.auth.repository import ExternalIdentityRepository, UserRepository
from src.modules.auth.schemas.external_auth.request import ExternalAuthRequestSchema
from src.modules.auth.schemas.telegram_mini_app import TelegramMiniAppAuthRequest
from src.modules.auth.telegram_init_data import validate_telegram_init_data
from src.modules.auth.utils import JWT, pw_manager
from src.utils.exceptions import ServiceError


class ExternalAuthService:
    def __init__(
        self,
        user_repository: UserRepository,
        external_identity_repository: ExternalIdentityRepository,
        jwt: JWT,
        unit_of_work: UnitOfWork,
    ):
        self.user_repo = user_repository
        self.external_identity_repo = external_identity_repository
        self.jwt = jwt
        self.uow = unit_of_work

    async def authenticate_external(
        self,
        provider: str,
        provider_user_id: str,
    ) -> dict:
        identity = await self.external_identity_repo.get_by_provider(
            provider=provider, provider_user_id=provider_user_id
        )

        if identity is None:
            user_id = uuid.uuid4()
            username = f"{provider}_{provider_user_id}"
            email = f"{provider}-{provider_user_id}@external.local"
            password = pw_manager.hash_password(secrets.token_urlsafe(32))

            user = await self.user_repo.create(
                id=user_id,
                username=username,
                email=email,
                password=password,
            )
            await self.external_identity_repo.create(
                provider=provider,
                provider_user_id=provider_user_id,
                user_id=user_id,
            )

            try:
                await self.uow.commit()
            except IntegrityError:
                await self.uow.rollback()
                identity = await self.external_identity_repo.get_by_provider(
                    provider=provider, provider_user_id=provider_user_id
                )
                if identity is None:
                    raise ServiceError(code=422, msg="User already exists")
                user = await self.user_repo.get_by_id(identity.user_id)
                if user is None:
                    raise ServiceError(code=422, msg="User does not exist")
        else:
            user = await self.user_repo.get_by_id(identity.user_id)
            if user is None:
                raise ServiceError(code=422, msg="User does not exist")

        user_id = str(user.id)
        access = self.jwt.create_access_token(user_id)
        refresh = self.jwt.create_refresh_token(user_id)

        return {
            "access": access,
            "refresh": refresh,
            "user": {
                "id": user.id,
                "username": user.username,
            },
        }

    async def authenticate_telegram_init_data(self, init_data: str) -> dict:
        telegram_user = validate_telegram_init_data(
            init_data,
            settings.BOT_TOKEN,
            settings.TELEGRAM_INIT_DATA_MAX_AGE_SECONDS,
        )
        return await self.authenticate_external(
            provider="telegram", provider_user_id=str(telegram_user["id"])
        )

    async def authenticate_request(
        self,
        data: ExternalAuthRequestSchema | TelegramMiniAppAuthRequest,
        bot_secret: str | None,
    ) -> dict:
        if isinstance(data, TelegramMiniAppAuthRequest):
            result = await self.authenticate_telegram_init_data(data.init_data)
            return {"access": result["access"], "user": result["user"]}

        expected_secret = settings.BOT_API_SECRET
        if (
            not bot_secret
            or not expected_secret
            or not hmac.compare_digest(bot_secret, expected_secret)
        ):
            raise ServiceError(code=401, msg="Invalid bot secret")
        return await self.authenticate_external(data.provider, data.provider_user_id)
