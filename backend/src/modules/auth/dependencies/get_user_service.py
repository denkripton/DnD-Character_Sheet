from fastapi import Depends
from src.databases.unit_of_work import UnitOfWork
from src.dependencies import get_unit_of_work
from src.modules.auth.dependencies.get_jwt_service import get_jwt_service
from src.modules.auth.dependencies.repositories import user_repository
from src.modules.auth.dependencies.user_service_factory import user_service_factory
from src.modules.auth.repository import UserRepository
from src.modules.auth.service import UserService
from src.modules.auth.utils import JWT


def get_user_service(
    user_repo: UserRepository = Depends(user_repository),
    jwt: JWT = Depends(get_jwt_service),
    uow: UnitOfWork = Depends(get_unit_of_work),
) -> UserService:
    return user_service_factory.create(user_repo=user_repo, jwt=jwt, unit_of_work=uow)
