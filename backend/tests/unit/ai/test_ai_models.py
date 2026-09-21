import asyncio

import pytest

from src.config import settings
from src.utils.exceptions import ServiceError
from src.modules.ai import AIGateway
from src.modules.ai.models import (
    AVAILABLE_MODELS,
    MODEL_PROVIDER,
    PROVIDER_MODELS,
    get_default_model,
)


class StubGateway:
    async def generate(self, prompt, model=None):
        return f"generated with {model}"


def _ai(default_model="gemini-2.5-flash"):
    return AIGateway(
        model_provider=MODEL_PROVIDER,
        providers={"gemini": StubGateway()},
        default_model=default_model,
    )


def test_available_models_not_empty():
    assert len(AVAILABLE_MODELS) > 0


def test_gemini_flash_available_by_default():
    assert "gemini-2.5-flash" in AVAILABLE_MODELS


def test_model_provider_mapping():
    assert MODEL_PROVIDER["gemini-2.5-flash"] == "gemini"


def test_providers_models_registered():
    for provider, models in PROVIDER_MODELS.items():
        for model in models:
            assert MODEL_PROVIDER[model] == provider


def test_default_model_falls_back_to_first_when_not_configured():
    original = settings.DEFAULT_AI_MODEL
    settings.DEFAULT_AI_MODEL = ""
    try:
        assert get_default_model() == AVAILABLE_MODELS[0]
    finally:
        settings.DEFAULT_AI_MODEL = original


def test_default_model_returns_configured_value():
    original = settings.DEFAULT_AI_MODEL
    settings.DEFAULT_AI_MODEL = "gemini-2.5-pro"
    try:
        assert get_default_model() == "gemini-2.5-pro"
    finally:
        settings.DEFAULT_AI_MODEL = original


def test_default_model_falls_back_when_configured_value_missing():
    original = settings.DEFAULT_AI_MODEL
    settings.DEFAULT_AI_MODEL = "unknown-model"
    try:
        assert get_default_model() == AVAILABLE_MODELS[0]
    finally:
        settings.DEFAULT_AI_MODEL = original


def test_ai_gateway_resolves_default_model():
    ai = _ai()

    async def flow():
        text = await ai.generate("prompt")
        assert text == "generated with gemini-2.5-flash"

    asyncio.run(flow())


def test_ai_gateway_uses_passed_model():
    ai = _ai()

    async def flow():
        text = await ai.generate("prompt", model="gemini-2.5-pro")
        assert text == "generated with gemini-2.5-pro"

    asyncio.run(flow())


def test_ai_gateway_unknown_model_raises():
    ai = _ai()

    async def flow():
        with pytest.raises(ServiceError) as exc_info:
            await ai.generate("prompt", model="gpt-5")
        assert exc_info.value.status_code == 422
        assert exc_info.value.message == "Model gpt-5 is not available"

    asyncio.run(flow())


def test_ai_gateway_missing_provider_raises():
    ai = AIGateway(
        model_provider={"gemini-2.5-flash": "deepseek"},
        providers={},
        default_model="gemini-2.5-flash",
    )

    async def flow():
        with pytest.raises(ServiceError) as exc_info:
            await ai.generate("prompt")
        assert exc_info.value.status_code == 422
        assert exc_info.value.message == "Provider deepseek is not implemented"

    asyncio.run(flow())


if __name__ == "__main__":
    for name, fn in sorted(globals().items()):
        if name.startswith("test_") and callable(fn):
            fn()
    print("ai models tests passed")