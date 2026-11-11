from src.databases.unit_of_work import UnitOfWork
from src.modules.auth.repository import UserRepository
from src.modules.auth.service import UserService
from src.modules.auth.utils import JWT


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
