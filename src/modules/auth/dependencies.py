from fastapi import Depends

from src.modules.auth.service import UserService
from src.modules.auth.repository import UserRepository
from src.dependencies import RepoFactory
from src.modules.auth.utils import JWT


user_repository = RepoFactory(repo=UserRepository)

def get_jwt() -> JWT:
    return JWT()


class UserServiceFactory:
    def __call__(
        self, 
        repo: UserRepository = Depends(user_repository),
        jwt: JWT = Depends(get_jwt)
        ):
        return UserService(user_repository=repo, jwt=jwt)

get_user_service = UserServiceFactory()