from typing import Protocol


class AIProvider(Protocol):
    name: str
    supported_models: list[str]

    async def generate(self, prompt: str, model: str) -> str: ...
