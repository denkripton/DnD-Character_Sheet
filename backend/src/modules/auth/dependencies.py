import hmac

from fastapi import Depends, HTTPException, Request, Response
from src.config import settings
from src.dependencies import RepoFactory, get_unit_of_work
from src.modules.auth.external_service import ExternalAuthService
from src.modules.auth.repository import ExternalIdentityRepository, UserRepository
from src.modules.auth.service import UserService
from src.modules.auth.utils import JWT
from src.utils.unit_of_work import UnitOfWork

user_repository = RepoFactory(repo=UserRepository)
external_identity_repository = RepoFactory(repo=ExternalIdentityRepository)

BOT_SECRET_HEADER = "X-Bot-Secret"


def get_jwt_service() -> JWT:
    return JWT()


class UserServiceFactory:
    def __init__(self, service_cls: type[UserService] = UserService):
        self.service_cls = service_cls

    def create(
        self,
        user_repo: UserRepository,
        jwt: JWT,
        unit_of_work: UnitOfWork,
    ) -> UserService:
        return self.service_cls(
            user_repository=user_repo,
            jwt=jwt,
            unit_of_work=unit_of_work,
        )


user_service_factory = UserServiceFactory()


def get_user_service(
    user_repo: UserRepository = Depends(user_repository),
    jwt: JWT = Depends(get_jwt_service),
    uow: UnitOfWork = Depends(get_unit_of_work),
) -> UserService:
    return user_service_factory.create(user_repo=user_repo, jwt=jwt, unit_of_work=uow)


async def get_current_user(
    request: Request, response: Response, jwt: JWT = Depends(get_jwt_service)
):
    auth_header: str | None = request.headers.get("Authorization")
    token = auth_header.replace("Bearer", "") if auth_header else None

    payload = jwt.validate_token(token)

    if payload:
        return payload["sub"]

    get_refresh_token = request.cookies.get("refresh_token")
    refresh_token = jwt.validate_token(get_refresh_token)

    if refresh_token is None:
        raise HTTPException(status_code=401, detail="User not authorized")

    new_access_token = jwt.create_access_token(refresh_token["sub"])

    response.headers["X-New-Access-Token"] = new_access_token

    return refresh_token["sub"]


class ExternalAuthServiceFactory:
    def __init__(self, service_cls: type[ExternalAuthService] = ExternalAuthService):
        self.service_cls = service_cls

    def create(
        self,
        user_repo: UserRepository,
        external_identity_repo: ExternalIdentityRepository,
        jwt: JWT,
        unit_of_work: UnitOfWork,
    ) -> ExternalAuthService:
        return self.service_cls(
            user_repository=user_repo,
            external_identity_repository=external_identity_repo,
            jwt=jwt,
            unit_of_work=unit_of_work,
        )


external_auth_service_factory = ExternalAuthServiceFactory()


def get_external_auth_service(
    user_repo: UserRepository = Depends(user_repository),
    external_identity_repo: ExternalIdentityRepository = Depends(
        external_identity_repository
    ),
    jwt: JWT = Depends(get_jwt_service),
    uow: UnitOfWork = Depends(get_unit_of_work),
) -> ExternalAuthService:
    return external_auth_service_factory.create(
        user_repo=user_repo,
        external_identity_repo=external_identity_repo,
        jwt=jwt,
        unit_of_work=uow,
    )


def require_bot_secret(request: Request) -> None:
    provided = request.headers.get(BOT_SECRET_HEADER)
    expected = settings.BOT_API_SECRET
    if not provided or not expected or not hmac.compare_digest(provided, expected):
        raise HTTPException(status_code=401, detail="Invalid bot secret")
