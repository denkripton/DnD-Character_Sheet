from src.config import settings
from src.infrastructure.ai.providers.gemini import GeminiProvider
from src.modules.ai.enums import AIProviderDefaults
from src.modules.ai.interfaces import AIProvider


def build_ai_providers() -> list[AIProvider]:
    providers: list[AIProvider] = []
    if settings.GEMINI_API_KEY:
        providers.append(
            GeminiProvider(
                api_key=settings.GEMINI_API_KEY,
                timeout_seconds=AIProviderDefaults.TIMEOUT_SECONDS.value,
            )
        )
    return providers
