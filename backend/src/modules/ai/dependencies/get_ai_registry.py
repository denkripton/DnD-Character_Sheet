from src.config import settings
from src.modules.ai.enums import AIProviderDefaults
from src.modules.ai.registry import AIProviderRegistry


def get_ai_registry() -> AIProviderRegistry:
    from src.infrastructure.ai import build_ai_providers

    providers = build_ai_providers()
    return AIProviderRegistry(
        providers=providers,
        default_model=settings.DEFAULT_AI_MODEL,
        preferred_provider=AIProviderDefaults.DEFAULT_PROVIDER.value,
    )
