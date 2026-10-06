from src.modules.ai.interfaces import AIProvider
from src.utils.exceptions import ServiceError


class AIProviderRegistry:
    def __init__(
        self,
        providers: list[AIProvider],
        default_model: str | None = None,
        preferred_provider: str | None = None,
    ):
        if not providers:
            raise ServiceError(code=422, msg="No AI provider is configured")
        self._providers = {provider.name: provider for provider in providers}
        self._model_provider = {
            model: provider.name
            for provider in providers
            for model in provider.supported_models
        }
        self._default_model = default_model
        self._preferred_provider = preferred_provider

    @property
    def provider_names(self) -> list[str]:
        return list(self._providers.keys())

    @property
    def models(self) -> list[str]:
        return list(self._model_provider.keys())

    @property
    def provider_models(self) -> dict[str, list[str]]:
        return {
            name: provider.supported_models
            for name, provider in self._providers.items()
        }

    @property
    def default_model(self) -> str:
        if self._default_model in self._model_provider:
            return self._default_model
        if self._preferred_provider in self._providers:
            preferred_models = self._providers[
                self._preferred_provider
            ].supported_models
            if preferred_models:
                return preferred_models[0]
        return next(iter(self._model_provider))

    def get_provider(self, name: str) -> AIProvider:
        provider = self._providers.get(name)
        if provider is None:
            raise ServiceError(code=422, msg=f"Provider {name} is not available")
        return provider

    def resolve(
        self, model: str | None = None, provider: str | None = None
    ) -> tuple[AIProvider, str]:
        if model is not None:
            mapped = self._model_provider.get(model)
            if mapped is None:
                raise ServiceError(code=422, msg=f"Model {model} is not available")
            if provider is not None and provider != mapped:
                raise ServiceError(
                    code=422,
                    msg=f"Model {model} is not available from provider {provider}",
                )
            return self._providers[mapped], model
        if provider is not None:
            impl = self.get_provider(provider)
            resolved_model = impl.supported_models[0]
            return impl, resolved_model
        resolved_model = self.default_model
        return self._providers[self._model_provider[resolved_model]], resolved_model
