from src.databases.unit_of_work import UnitOfWork
from src.modules.auth.external_service import ExternalAuthService
from src.modules.auth.repository import ExternalIdentityRepository, UserRepository
from src.modules.auth.utils import JWT


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
