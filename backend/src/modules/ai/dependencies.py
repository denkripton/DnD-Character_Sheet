from src.config import settings
from src.modules.ai.enums import AIProviderDefaults
from src.modules.ai.registry import AIProviderRegistry
from src.modules.ai.service import AIService


def get_ai_registry() -> AIProviderRegistry:
    from src.infrastructure.ai import build_ai_providers

    providers = build_ai_providers()
    return AIProviderRegistry(
        providers=providers,
        default_model=settings.DEFAULT_AI_MODEL,
        preferred_provider=AIProviderDefaults.DEFAULT_PROVIDER.value,
    )


def get_ai_service() -> AIService:
    return AIService(registry=get_ai_registry())
