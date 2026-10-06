import asyncio

import pytest
from src.modules.ai import AIProviderRegistry, AIService
from src.utils.exceptions import (
    AIProviderError,
    AIProviderRateLimitError,
    ServiceError,
)


class StubProvider:
    def __init__(self, name, models, error=None):
        self.name = name
        self.supported_models = models
        self.error = error
        self.calls = []

    async def generate(self, prompt, model):
        self.calls.append({"prompt": prompt, "model": model})
        if self.error is not None:
            raise self.error
        return f"{self.name}:{model}:{prompt}"


def _registry(default_model="alpha-1", preferred_provider=None):
    return AIProviderRegistry(
        providers=[
            StubProvider("alpha", ["alpha-1", "alpha-2"]),
            StubProvider("beta", ["beta-1"]),
        ],
        default_model=default_model,
        preferred_provider=preferred_provider,
    )


def test_registry_lists_providers_and_models():
    registry = _registry()

    assert registry.provider_names == ["alpha", "beta"]
    assert registry.models == ["alpha-1", "alpha-2", "beta-1"]
    assert registry.provider_models == {
        "alpha": ["alpha-1", "alpha-2"],
        "beta": ["beta-1"],
    }


def test_registry_empty_providers_raises():
    with pytest.raises(ServiceError) as exc_info:
        AIProviderRegistry(providers=[])
    assert exc_info.value.status_code == 422
    assert exc_info.value.message == "No AI provider is configured"


def test_registry_default_model_configured():
    registry = _registry(default_model="beta-1")
    assert registry.default_model == "beta-1"


def test_registry_default_model_falls_back_to_preferred_provider():
    registry = _registry(default_model="missing", preferred_provider="beta")
    assert registry.default_model == "beta-1"


def test_registry_default_model_falls_back_to_first():
    registry = _registry(default_model="missing", preferred_provider="missing")
    assert registry.default_model == "alpha-1"


def test_registry_resolve_default_model():
    registry = _registry()
    provider, model = registry.resolve()
    assert provider.name == "alpha"
    assert model == "alpha-1"


def test_registry_resolve_explicit_model():
    registry = _registry()
    provider, model = registry.resolve(model="beta-1")
    assert provider.name == "beta"
    assert model == "beta-1"


def test_registry_resolve_explicit_provider():
    registry = _registry()
    provider, model = registry.resolve(provider="beta")
    assert provider.name == "beta"
    assert model == "beta-1"


def test_registry_resolve_unknown_model_raises():
    registry = _registry()
    with pytest.raises(ServiceError) as exc_info:
        registry.resolve(model="gpt-5")
    assert exc_info.value.status_code == 422
    assert exc_info.value.message == "Model gpt-5 is not available"


def test_registry_resolve_unknown_provider_raises():
    registry = _registry()
    with pytest.raises(ServiceError) as exc_info:
        registry.resolve(provider="deepseek")
    assert exc_info.value.status_code == 422
    assert exc_info.value.message == "Provider deepseek is not available"


def test_registry_resolve_model_provider_mismatch_raises():
    registry = _registry()
    with pytest.raises(ServiceError) as exc_info:
        registry.resolve(model="alpha-1", provider="beta")
    assert exc_info.value.status_code == 422
    assert exc_info.value.message == (
        "Model alpha-1 is not available from provider beta"
    )


def test_ai_service_resolves_default_model():
    service = AIService(registry=_registry())

    async def flow():
        text = await service.generate("hello")
        assert text == "alpha:alpha-1:hello"

    asyncio.run(flow())


def test_ai_service_uses_explicit_model_and_provider():
    service = AIService(registry=_registry())

    async def flow():
        text = await service.generate("hello", model="beta-1", provider="beta")
        assert text == "beta:beta-1:hello"

    asyncio.run(flow())


def test_ai_service_unknown_model_raises():
    service = AIService(registry=_registry())

    async def flow():
        with pytest.raises(ServiceError) as exc_info:
            await service.generate("hello", model="gpt-5")
        assert exc_info.value.status_code == 422

    asyncio.run(flow())


def test_ai_service_propagates_provider_error():
    provider = StubProvider(
        "alpha", ["alpha-1"], error=AIProviderRateLimitError("rate limited", provider="alpha")
    )
    registry = AIProviderRegistry(providers=[provider])
    service = AIService(registry=registry)

    async def flow():
        with pytest.raises(AIProviderRateLimitError) as exc_info:
            await service.generate("hello")
        assert exc_info.value.message == "rate limited"
        assert exc_info.value.provider == "alpha"

    asyncio.run(flow())


def test_ai_service_propagates_generic_provider_error():
    provider = StubProvider(
        "alpha", ["alpha-1"], error=AIProviderError("boom", provider="alpha")
    )
    registry = AIProviderRegistry(providers=[provider])
    service = AIService(registry=registry)

    async def flow():
        with pytest.raises(AIProviderError) as exc_info:
            await service.generate("hello")
        assert exc_info.value.message == "boom"

    asyncio.run(flow())


if __name__ == "__main__":
    for name, fn in sorted(globals().items()):
        if name.startswith("test_") and callable(fn):
            fn()
    print("ai service tests passed")
