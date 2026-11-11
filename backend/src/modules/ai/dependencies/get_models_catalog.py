from src.config import settings
from src.modules.ai import dependencies
from src.modules.ai.enums import AICatalogCacheKey


async def get_models_catalog() -> list[dict]:
    cached = await dependencies.cache.get(AICatalogCacheKey.MODELS.value)
    if cached is not None:
        return cached
    registry = dependencies.get_ai_registry()
    payload = [
        {"provider": provider, "model": model}
        for provider, models in registry.provider_models.items()
        for model in models
    ]
    await dependencies.cache.set(
        AICatalogCacheKey.MODELS.value,
        payload,
        ttl=settings.CACHE_METADATA_TTL,
    )
    return payload
