from fastapi import Depends

from src.config import settings
from src.utils.exceptions import ServiceError
from src.modules.ai.client import AIGateway
from src.modules.ai.gateway import GeminiGateway
from src.modules.ai.models import MODEL_PROVIDER, get_default_model


def get_ai_client() -> AIGateway:
    if not settings.GEMINI_API_KEY:
        raise ServiceError(code=422, msg="Gemini API key is not configured")
    return AIGateway(
        model_provider=MODEL_PROVIDER,
        providers={"gemini": GeminiGateway(api_key=settings.GEMINI_API_KEY)},
        default_model=get_default_model(),
    )


__all__ = ["get_ai_client"]