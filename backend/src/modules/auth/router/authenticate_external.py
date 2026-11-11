from fastapi import APIRouter, Depends, Header
from src.modules.auth.dependencies import (
    BOT_SECRET_HEADER,
    get_external_auth_service,
)
from src.modules.auth.external_service import ExternalAuthService
from src.modules.auth.schemas.external_auth.read import ExternalAuthSchema
from src.modules.auth.schemas.external_auth.request import ExternalAuthRequestSchema
from src.modules.auth.schemas.telegram_mini_app import (
    TelegramMiniAppAuthRequest,
    TelegramMiniAppAuthResponse,
)
from src.utils import ErrorHandlingRoute

router = APIRouter(route_class=ErrorHandlingRoute)


@router.post(
    "/auth/external",
    summary="External authentication",
    tags=["Authentication"],
    description="Authenticate a user through a trusted external service",
    response_model=ExternalAuthSchema | TelegramMiniAppAuthResponse,
)
async def authenticate_external(
    data: ExternalAuthRequestSchema | TelegramMiniAppAuthRequest,
    bot_secret: str | None = Header(default=None, alias=BOT_SECRET_HEADER),
    service: ExternalAuthService = Depends(get_external_auth_service),
):
    return await service.authenticate_request(data=data, bot_secret=bot_secret)
