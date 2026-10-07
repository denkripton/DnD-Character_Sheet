import asyncio
from typing import ClassVar

from src.config import settings
from src.infrastructure.redis.cache import RedisCache
from src.modules.ai import dependencies as ai_dependencies
from src.modules.ai.registry import AIProviderRegistry
from tests.utils import FakeRedis

MODELS_KEY = "ai:models:catalog"
PROVIDERS_KEY = "ai:providers:catalog"


class StubProvider:
    name = "gemini"
    supported_models: ClassVar[list[str]] = ["gemini-1", "gemini-2"]

    async def generate(self, prompt, model):
        return f"{model}:{prompt}"


def _patch(monkeypatch, fake_redis):
    counter = {"builds": 0}

    def factory():
        counter["builds"] += 1
        return AIProviderRegistry(
            providers=[StubProvider()],
            default_model="gemini-1",
            preferred_provider="gemini",
        )

    monkeypatch.setattr(
        "src.modules.ai.dependencies.cache", RedisCache(fake_redis)
    )
    monkeypatch.setattr("src.modules.ai.dependencies.get_ai_registry", factory)
    return counter


def test_models_catalog_cache_miss_populates(monkeypatch):
    fake = FakeRedis()
    counter = _patch(monkeypatch, fake)

    async def flow():
        payload = await ai_dependencies.get_models_catalog()

        assert payload == [
            {"provider": "gemini", "model": "gemini-1"},
            {"provider": "gemini", "model": "gemini-2"},
        ]
        assert counter["builds"] == 1
        assert MODELS_KEY in fake.store
        assert fake.expirations[MODELS_KEY] == settings.CACHE_METADATA_TTL

    asyncio.run(flow())


def test_models_catalog_cache_hit_skips_registry_build(monkeypatch):
    fake = FakeRedis()
    counter = _patch(monkeypatch, fake)

    async def flow():
        first = await ai_dependencies.get_models_catalog()
        second = await ai_dependencies.get_models_catalog()

        assert first == second
        assert counter["builds"] == 1

    asyncio.run(flow())


def test_providers_catalog_cached_under_separate_key(monkeypatch):
    fake = FakeRedis()
    counter = _patch(monkeypatch, fake)

    async def flow():
        models = await ai_dependencies.get_models_catalog()
        providers = await ai_dependencies.get_providers_catalog()

        assert MODELS_KEY in fake.store
        assert PROVIDERS_KEY in fake.store
        assert providers == [
            {"name": "gemini", "models": ["gemini-1", "gemini-2"]}
        ]
        assert counter["builds"] == 2

        cached_models = await ai_dependencies.get_models_catalog()
        cached_providers = await ai_dependencies.get_providers_catalog()
        assert cached_models == models
        assert cached_providers == providers
        assert counter["builds"] == 2

    asyncio.run(flow())


def test_models_catalog_expires_and_rebuilds(monkeypatch):
    fake = FakeRedis()
    counter = _patch(monkeypatch, fake)

    async def flow():
        await ai_dependencies.get_models_catalog()
        assert counter["builds"] == 1

        fake.advance(settings.CACHE_METADATA_TTL + 1)
        assert MODELS_KEY not in fake.store

        payload = await ai_dependencies.get_models_catalog()
        assert payload[0]["model"] == "gemini-1"
        assert counter["builds"] == 2

    asyncio.run(flow())


def test_catalog_survives_redis_failure(monkeypatch):
    fake = FakeRedis(fail=True)
    counter = _patch(monkeypatch, fake)

    async def flow():
        models = await ai_dependencies.get_models_catalog()
        providers = await ai_dependencies.get_providers_catalog()

        assert models == [
            {"provider": "gemini", "model": "gemini-1"},
            {"provider": "gemini", "model": "gemini-2"},
        ]
        assert providers == [
            {"name": "gemini", "models": ["gemini-1", "gemini-2"]}
        ]
        assert counter["builds"] == 2

        again = await ai_dependencies.get_models_catalog()
        assert again == models
        assert counter["builds"] == 3

    asyncio.run(flow())
