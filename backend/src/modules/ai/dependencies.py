from src.config import settings
from src.infrastructure.redis import cache
from src.modules.ai.enums import AIProviderDefaults
from src.modules.ai.registry import AIProviderRegistry
from src.modules.ai.service import AIService

MODELS_CATALOG_KEY = "ai:models:catalog"
PROVIDERS_CATALOG_KEY = "ai:providers:catalog"


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


async def get_models_catalog() -> list[dict]:
    cached = await cache.get(MODELS_CATALOG_KEY)
    if cached is not None:
        return cached
    registry = get_ai_registry()
    payload = [
        {"provider": provider, "model": model}
        for provider, models in registry.provider_models.items()
        for model in models
    ]
    await cache.set(MODELS_CATALOG_KEY, payload, ttl=settings.CACHE_METADATA_TTL)
    return payload


async def get_providers_catalog() -> list[dict]:
    cached = await cache.get(PROVIDERS_CATALOG_KEY)
    if cached is not None:
        return cached
    registry = get_ai_registry()
    payload = [
        {"name": name, "models": models}
        for name, models in registry.provider_models.items()
    ]
    await cache.set(PROVIDERS_CATALOG_KEY, payload, ttl=settings.CACHE_METADATA_TTL)
    return payload
