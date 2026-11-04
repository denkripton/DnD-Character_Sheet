from src.config import settings
from src.infrastructure.redis import cache
from src.modules.ai.enums import AICatalogCacheKey, AIProviderDefaults
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


async def get_models_catalog() -> list[dict]:
    cached = await cache.get(AICatalogCacheKey.MODELS.value)
    if cached is not None:
        return cached
    registry = get_ai_registry()
    payload = [
        {"provider": provider, "model": model}
        for provider, models in registry.provider_models.items()
        for model in models
    ]
    await cache.set(AICatalogCacheKey.MODELS.value, payload, ttl=settings.CACHE_METADATA_TTL)
    return payload


async def get_providers_catalog() -> list[dict]:
    cached = await cache.get(AICatalogCacheKey.PROVIDERS.value)
    if cached is not None:
        return cached
    registry = get_ai_registry()
    payload = [
        {"name": name, "models": models}
        for name, models in registry.provider_models.items()
    ]
    await cache.set(AICatalogCacheKey.PROVIDERS.value, payload, ttl=settings.CACHE_METADATA_TTL)
    return payload
