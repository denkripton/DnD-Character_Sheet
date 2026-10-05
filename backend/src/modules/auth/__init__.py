from src.modules.auth.dependencies import (
    external_identity_repository,
    get_current_user,
    get_external_auth_service,
    get_user_service,
    require_bot_secret,
    user_repository,
)
from src.modules.auth.external_service import ExternalAuthService
from src.modules.auth.router import user_router
from src.modules.auth.service import UserService

__all__ = [
    "ExternalAuthService",
    "UserService",
    "external_identity_repository",
    "get_current_user",
    "get_external_auth_service",
    "get_user_service",
    "require_bot_secret",
    "user_repository",
    "user_router",
]
