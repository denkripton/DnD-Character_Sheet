from src.config import settings

PROVIDER_MODELS: dict[str, list[str]] = {
    "gemini": ["gemini-2.5-flash", "gemini-2.5-pro"],
}

MODEL_PROVIDER: dict[str, str] = {
    model: provider
    for provider, models in PROVIDER_MODELS.items()
    for model in models
}

AVAILABLE_MODELS: list[str] = list(MODEL_PROVIDER)


def get_default_model() -> str:
    if settings.DEFAULT_AI_MODEL in AVAILABLE_MODELS:
        return settings.DEFAULT_AI_MODEL
    return AVAILABLE_MODELS[0]