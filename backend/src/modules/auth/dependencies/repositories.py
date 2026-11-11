from src.dependencies import RepoFactory
from src.modules.auth.repository import ExternalIdentityRepository, UserRepository

user_repository = RepoFactory(repo=UserRepository)
external_identity_repository = RepoFactory(repo=ExternalIdentityRepository)
