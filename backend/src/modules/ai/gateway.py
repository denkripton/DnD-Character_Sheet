from google.genai import Client, types


class GeminiGateway:
    def __init__(self, api_key: str, model: str = "gemini-2.5-flash"):
        self._client = Client(api_key=api_key)
        self._model = model

    async def generate(self, prompt: str, model: str | None = None) -> str:
        response = await self._client.aio.models.generate_content(
            model=model or self._model,
            contents=prompt,
            config=types.GenerateContentConfig(
                thinking_config=types.ThinkingConfig(thinking_budget=0)
            ),
        )
        return response.text or ""