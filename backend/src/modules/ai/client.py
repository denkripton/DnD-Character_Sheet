from src.exceptions import ServiceError


class AIGateway:
    def __init__(
        self,
        model_provider: dict[str, str],
        providers: dict[str, object],
        default_model: str,
    ):
        self._model_provider = model_provider
        self._providers = providers
        self._default_model = default_model

    async def generate(self, prompt: str, model: str | None = None) -> str:
        model = model or self._default_model

        provider = self._model_provider.get(model)
        if provider is None:
            raise ServiceError(code=422, msg=f"Model {model} is not available")

        gateway = self._providers.get(provider)
        if gateway is None:
            raise ServiceError(code=422, msg=f"Provider {provider} is not implemented")

        return await gateway.generate(prompt, model=model)