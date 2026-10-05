import secrets
import uuid

from sqlalchemy.exc import IntegrityError
from src.modules.auth.repository import ExternalIdentityRepository, UserRepository
from src.modules.auth.utils import JWT, pw_manager
from src.utils.exceptions import ServiceError
from src.utils.unit_of_work import UnitOfWork


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