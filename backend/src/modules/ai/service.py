from src.modules.ai.registry import AIProviderRegistry


class AIService:
    def __init__(self, registry: AIProviderRegistry):
        self._registry = registry

    @property
    def registry(self) -> AIProviderRegistry:
        return self._registry

    async def generate(
        self,
        prompt: str,
        model: str | None = None,
        provider: str | None = None,
    ) -> str:
        resolved_provider, resolved_model = self._registry.resolve(
            model=model, provider=provider
        )
        return await resolved_provider.generate(prompt, model=resolved_model)
