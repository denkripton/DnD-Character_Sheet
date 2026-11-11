from src.config import settings
from src.modules.ai import dependencies
from src.modules.ai.enums import AICatalogCacheKey


async def get_providers_catalog() -> list[dict]:
    cached = await dependencies.cache.get(AICatalogCacheKey.PROVIDERS.value)
    if cached is not None:
        return cached
    registry = dependencies.get_ai_registry()
    payload = [
        {"name": name, "models": models}
        for name, models in registry.provider_models.items()
    ]
    await dependencies.cache.set(
        AICatalogCacheKey.PROVIDERS.value,
        payload,
        ttl=settings.CACHE_METADATA_TTL,
    )
    return payload
