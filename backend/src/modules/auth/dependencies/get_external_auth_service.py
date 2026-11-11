from fastapi import Depends
from src.databases.unit_of_work import UnitOfWork
from src.dependencies import get_unit_of_work
from src.modules.auth.dependencies.external_auth_service_factory import (
    external_auth_service_factory,
)
from src.modules.auth.dependencies.get_jwt_service import get_jwt_service
from src.modules.auth.dependencies.repositories import (
    external_identity_repository,
    user_repository,
)
from src.modules.auth.external_service import ExternalAuthService
from src.modules.auth.repository import ExternalIdentityRepository, UserRepository
from src.modules.auth.utils import JWT


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
