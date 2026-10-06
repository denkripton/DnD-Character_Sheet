import asyncio
from typing import ClassVar

from google.genai import Client, types
from google.genai import errors as genai_errors

from src.modules.ai.enums import GEMINI_SUPPORTED_MODELS, AIProviderName
from src.utils.exceptions import (
    AIProviderAuthError,
    AIProviderError,
    AIProviderRateLimitError,
    AIProviderTimeoutError,
)


class GeminiProvider:
    name = AIProviderName.GEMINI
    supported_models: ClassVar[list[str]] = list(GEMINI_SUPPORTED_MODELS)

    def __init__(self, api_key: str, timeout_seconds: float = 30.0, client=None):
        self._client = client if client is not None else Client(api_key=api_key)
        self._timeout_seconds = timeout_seconds

    async def generate(self, prompt: str, model: str) -> str:
        if model not in self.supported_models:
            raise AIProviderError(
                f"Model {model} is not supported by {self.name}",
                provider=self.name,
            )
        try:
            response = await asyncio.wait_for(
                self._client.aio.models.generate_content(
                    model=model,
                    contents=prompt,
                    config=types.GenerateContentConfig(
                        thinking_config=types.ThinkingConfig(thinking_budget=0)
                    ),
                ),
                timeout=self._timeout_seconds,
            )
        except TimeoutError as exc:
            raise AIProviderTimeoutError(
                f"{self.name} request timed out", provider=self.name
            ) from exc
        except genai_errors.ClientError as exc:
            status = getattr(exc, "code", None)
            if status == 429:
                raise AIProviderRateLimitError(
                    f"{self.name} rate limit exceeded", provider=self.name
                ) from exc
            if status in (401, 403):
                raise AIProviderAuthError(
                    f"{self.name} authentication failed", provider=self.name
                ) from exc
            raise AIProviderError(
                f"{self.name} request failed: {exc}", provider=self.name
            ) from exc
        except genai_errors.ServerError as exc:
            raise AIProviderError(
                f"{self.name} server error: {exc}", provider=self.name
            ) from exc
        except Exception as exc:
            raise AIProviderError(
                f"{self.name} request failed: {exc}", provider=self.name
            ) from exc
        return response.text or ""
