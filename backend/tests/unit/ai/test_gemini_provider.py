import asyncio
from unittest.mock import AsyncMock, MagicMock

import pytest
from google.genai import errors as genai_errors
from src.infrastructure.ai.providers.gemini import GeminiProvider
from src.utils.exceptions import (
    AIProviderAuthError,
    AIProviderError,
    AIProviderRateLimitError,
    AIProviderTimeoutError,
)


def _provider(response=None, side_effect=None, timeout=30.0):
    generate = AsyncMock(side_effect=side_effect)
    if response is not None:
        generate.return_value = response
    client = MagicMock()
    client.aio.models.generate_content = generate
    return GeminiProvider(
        api_key="test-key", timeout_seconds=timeout, client=client
    ), generate


def test_generate_returns_text():
    response = MagicMock(text="story text")
    provider, generate = _provider(response=response)

    async def flow():
        result = await provider.generate("prompt", model="gemini-2.5-flash")
        assert result == "story text"
        generate.assert_awaited_once()
        kwargs = generate.await_args.kwargs
        assert kwargs["model"] == "gemini-2.5-flash"
        assert kwargs["contents"] == "prompt"

    asyncio.run(flow())


def test_generate_empty_text_returns_empty_string():
    response = MagicMock(text=None)
    provider, _ = _provider(response=response)

    async def flow():
        result = await provider.generate("prompt", model="gemini-2.5-flash")
        assert result == ""

    asyncio.run(flow())


def test_generate_unsupported_model_raises():
    provider, generate = _provider(response=MagicMock(text="x"))

    async def flow():
        with pytest.raises(AIProviderError) as exc_info:
            await provider.generate("prompt", model="unknown-model")
        assert exc_info.value.provider == "gemini"
        generate.assert_not_awaited()

    asyncio.run(flow())


def test_generate_timeout_raises():
    provider, _ = _provider(side_effect=TimeoutError(), timeout=0.01)

    async def flow():
        with pytest.raises(AIProviderTimeoutError) as exc_info:
            await provider.generate("prompt", model="gemini-2.5-flash")
        assert exc_info.value.provider == "gemini"

    asyncio.run(flow())


def test_generate_rate_limit_raises():
    error = genai_errors.ClientError(code=429, response_json={"error": {"message": "quota exceeded"}})
    provider, _ = _provider(side_effect=error)

    async def flow():
        with pytest.raises(AIProviderRateLimitError) as exc_info:
            await provider.generate("prompt", model="gemini-2.5-flash")
        assert exc_info.value.provider == "gemini"

    asyncio.run(flow())


def test_generate_auth_error_raises():
    error = genai_errors.ClientError(code=401, response_json={"error": {"message": "unauthorized"}})
    provider, _ = _provider(side_effect=error)

    async def flow():
        with pytest.raises(AIProviderAuthError) as exc_info:
            await provider.generate("prompt", model="gemini-2.5-flash")
        assert exc_info.value.provider == "gemini"

    asyncio.run(flow())


def test_generate_client_error_raises_provider_error():
    error = genai_errors.ClientError(code=400, response_json={"error": {"message": "bad request"}})
    provider, _ = _provider(side_effect=error)

    async def flow():
        with pytest.raises(AIProviderError) as exc_info:
            await provider.generate("prompt", model="gemini-2.5-flash")
        assert "request failed" in exc_info.value.message

    asyncio.run(flow())


def test_generate_server_error_raises_provider_error():
    error = genai_errors.ServerError(code=503, response_json={"error": {"message": "unavailable"}})
    provider, _ = _provider(side_effect=error)

    async def flow():
        with pytest.raises(AIProviderError) as exc_info:
            await provider.generate("prompt", model="gemini-2.5-flash")
        assert "server error" in exc_info.value.message

    asyncio.run(flow())


def test_generate_unexpected_error_raises_provider_error():
    provider, _ = _provider(side_effect=ValueError("sdk exploded"))

    async def flow():
        with pytest.raises(AIProviderError) as exc_info:
            await provider.generate("prompt", model="gemini-2.5-flash")
        assert "request failed" in exc_info.value.message

    asyncio.run(flow())


def test_supported_models_registered():
    provider = GeminiProvider(api_key="test-key", client=MagicMock())
    assert provider.name == "gemini"
    assert "gemini-2.5-flash" in provider.supported_models
    assert "gemini-2.5-pro" in provider.supported_models


if __name__ == "__main__":
    for name, fn in sorted(globals().items()):
        if name.startswith("test_") and callable(fn):
            fn()
    print("gemini provider tests passed")
