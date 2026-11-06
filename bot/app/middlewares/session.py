from typing import Any

from aiogram import BaseMiddleware
from aiogram.types import CallbackQuery, Message

from app.infrastructure.http.exceptions import BackendAuthError
from app.modules.auth import PROVIDER_TELEGRAM, BotAuthService
from app.presentation.messages import AUTH_UNAVAILABLE_TEXT


async def restore_session(
    state, auth_service: BotAuthService, user_id: int, refresh: bool = False
) -> None:
    data = await state.get_data()
    auth = data.get("auth")
    valid = (
        isinstance(auth, dict)
        and auth.get("provider") == PROVIDER_TELEGRAM
        and auth.get("provider_user_id") == str(user_id)
        and bool(auth.get("user_id"))
    )
    if data and not valid:
        await state.clear()
    if valid and not refresh:
        return
    context = await auth_service.authenticate(user_id)
    if valid and context.user_id != auth["user_id"]:
        await state.clear()
    await state.update_data(auth=context.model_dump())


class SessionMiddleware(BaseMiddleware):
    async def __call__(self, handler, event, data: dict[str, Any]) -> Any:
        state = data.get("state")
        user = getattr(event, "from_user", None)
        if state is None or user is None or user.id <= 0:
            return await handler(event, data)

        if isinstance(event, Message):
            command = (event.text or "").split(maxsplit=1)[0].split("@", 1)[0]
            if command == "/start":
                return await handler(event, data)
            needs_session = (
                command
                in {"/create", "/create_character", "/edit_character", "/backstory", "/back", "/cancel"}
                or (event.text or "") in {"Create Character", "My Characters", "Open Mini App", "Help"}
                or await state.get_state() is not None
            )
        else:
            needs_session = isinstance(event, CallbackQuery) and (
                event.data or ""
            ).startswith(("cc:", "bs:", "cm:"))

        auth = (await state.get_data()).get("auth")
        if isinstance(auth, dict) and auth.get("provider_user_id") != str(user.id):
            needs_session = True
        if needs_session:
            try:
                await restore_session(state, data["auth_service"], user.id)
            except BackendAuthError:
                if isinstance(event, CallbackQuery):
                    await event.answer(AUTH_UNAVAILABLE_TEXT, show_alert=True)
                else:
                    await event.answer(AUTH_UNAVAILABLE_TEXT)
                return None
        return await handler(event, data)
