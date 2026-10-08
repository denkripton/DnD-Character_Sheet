from app.messaging import MessageType

CHARACTER_COMMAND_TIMEOUT = 10.0
FALLBACK_ERROR_TEXT = "Something went wrong. Please try again."


class CharacterCreationError(Exception):
    pass


class BackendUnavailableError(Exception):
    pass


class CharacterCreationService:
    def __init__(self, rabbit, timeout: float = CHARACTER_COMMAND_TIMEOUT):
        self._rabbit = rabbit
        self._timeout = timeout

    async def start(self, auth: dict) -> dict:
        payload = await self._request(MessageType.CHARACTER_CREATE, {}, auth)
        return self._extract_draft(payload)

    async def set_value(
        self, auth: dict, draft_id: str, parameter: str, value: str
    ) -> dict:
        payload = await self._request(
            MessageType.CHARACTER_UPDATE_PARAMETER,
            {"draft_id": draft_id, "parameter": parameter, "value": value},
            auth,
        )
        return self._extract_draft(payload)

    async def generate_value(
        self, auth: dict, draft_id: str, parameter: str
    ) -> dict:
        payload = await self._request(
            MessageType.CHARACTER_UPDATE_PARAMETER,
            {"draft_id": draft_id, "parameter": parameter, "generate": True},
            auth,
        )
        return self._extract_draft(payload)

    async def generate_character(
        self, auth: dict, draft_id: str, method: str
    ) -> dict:
        payload = await self._request(
            MessageType.CHARACTER_GENERATE,
            {"draft_id": draft_id, "method": method},
            auth,
        )
        draft = self._extract_draft(payload)
        return {
            "draft": draft,
            "stats": payload.get("stats"),
            "modifiers": payload.get("modifiers"),
        }

    async def generate_stats(
        self, auth: dict, draft_id: str, method: str
    ) -> dict:
        payload = await self._request(
            MessageType.CHARACTER_STATS,
            {"draft_id": draft_id, "method": method},
            auth,
        )
        return self._extract_stats(payload)

    async def set_stats(self, auth: dict, draft_id: str, values: list) -> dict:
        payload = await self._request(
            MessageType.CHARACTER_STATS,
            {"draft_id": draft_id, "values": values},
            auth,
        )
        return self._extract_stats(payload)

    async def cancel(self, auth: dict, draft_id: str) -> None:
        await self._request(
            MessageType.CHARACTER_DELETE, {"draft_id": draft_id}, auth
        )

    async def save_character(self, auth: dict, draft_id: str) -> dict:
        payload = await self._request(
            MessageType.CHARACTER_SAVE, {"draft_id": draft_id}, auth
        )
        character_id = payload.get("character_id")
        character = payload.get("character")
        if not character_id or not isinstance(character, dict):
            raise CharacterCreationError(FALLBACK_ERROR_TEXT)
        return {"character_id": character_id, "character": character}

    async def generate_backstory(
        self,
        auth: dict,
        character_id: str,
        prompt: str | None = None,
        model: str | None = None,
        provider: str | None = None,
    ) -> str:
        request = {"character_id": character_id, "prompt": prompt}
        if model is not None:
            request["model"] = model
        if provider is not None:
            request["provider"] = provider
        payload = await self._request(
            MessageType.CHARACTER_GENERATE_BACKSTORY,
            request,
            auth,
        )
        backstory = payload.get("backstory")
        if not isinstance(backstory, str) or not backstory:
            raise CharacterCreationError(FALLBACK_ERROR_TEXT)
        return backstory

    async def get_ai_catalog(self, auth: dict) -> list[dict[str, object]]:
        payload = await self._request(MessageType.AI_CATALOG, {}, auth)
        providers = payload.get("providers")
        if not isinstance(providers, list):
            raise CharacterCreationError(FALLBACK_ERROR_TEXT)
        catalog = []
        for provider in providers:
            if not isinstance(provider, dict):
                raise CharacterCreationError(FALLBACK_ERROR_TEXT)
            name = provider.get("name")
            models = provider.get("models")
            if not isinstance(name, str) or not isinstance(models, list):
                raise CharacterCreationError(FALLBACK_ERROR_TEXT)
            if not all(isinstance(model, str) for model in models):
                raise CharacterCreationError(FALLBACK_ERROR_TEXT)
            catalog.append({"name": name, "models": models})
        return catalog

    async def save_backstory(
        self, auth: dict, character_id: str, backstory: str
    ) -> str:
        payload = await self._request(
            MessageType.CHARACTER_SAVE_BACKSTORY,
            {"character_id": character_id, "backstory": backstory},
            auth,
        )
        saved = payload.get("backstory")
        if not isinstance(saved, str):
            raise CharacterCreationError(FALLBACK_ERROR_TEXT)
        return saved

    async def _request(self, message_type, payload, auth: dict) -> dict:
        try:
            envelope = await self._rabbit.request(
                message_type,
                payload,
                timeout=self._timeout,
                provider=auth.get("provider"),
                provider_user_id=auth.get("provider_user_id"),
                user_id=auth.get("user_id"),
            )
        except Exception as exc:
            raise BackendUnavailableError(str(exc)) from exc
        response = envelope.payload
        if not isinstance(response, dict):
            raise CharacterCreationError(FALLBACK_ERROR_TEXT)
        if not response.get("ok"):
            raise CharacterCreationError(response.get("error") or FALLBACK_ERROR_TEXT)
        return response

    @staticmethod
    def _extract_draft(payload: dict) -> dict:
        draft = payload.get("draft")
        if not isinstance(draft, dict):
            raise CharacterCreationError(FALLBACK_ERROR_TEXT)
        return draft

    @staticmethod
    def _extract_stats(payload: dict) -> dict:
        stats = payload.get("stats")
        if not isinstance(stats, dict):
            raise CharacterCreationError(FALLBACK_ERROR_TEXT)
        return {
            "stats": stats,
            "modifiers": payload.get("modifiers"),
        }
