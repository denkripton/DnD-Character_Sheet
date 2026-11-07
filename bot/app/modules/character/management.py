from aiogram import F, Router
from aiogram.types import (
    CallbackQuery,
    InlineKeyboardButton,
    InlineKeyboardMarkup,
    Message,
)

from app.messaging import MessageType
from app.modules.character.keyboards import navigation_keyboard
from app.modules.character.router import _summary_text
from app.modules.character.service import (
    BackendUnavailableError,
    CharacterCreationError,
)
from app.modules.character.sheet import (
    SHEET_SECTIONS,
    sheet_keyboard,
    sheet_page_count,
    sheet_text,
)
from app.modules.character.states import CharacterCreationStates
from app.presentation.messages import CHARACTER_UNAVAILABLE_TEXT


class CharacterManagementService:
    def __init__(self, rabbit, timeout: float = 10.0):
        self.rabbit = rabbit
        self.timeout = timeout

    async def list(self, auth: dict) -> list[dict]:
        try:
            envelope = await self.rabbit.request(
                MessageType.CHARACTER_LIST, {}, timeout=self.timeout,
                provider=auth.get("provider"), provider_user_id=auth.get("provider_user_id"), user_id=auth.get("user_id"),
            )
        except Exception as exc:
            raise BackendUnavailableError(str(exc)) from exc
        payload = envelope.payload
        if not isinstance(payload, dict) or not payload.get("ok"):
            raise CharacterCreationError((payload or {}).get("error", "Unable to load characters."))
        characters = payload.get("characters", [])
        if not isinstance(characters, list) or not all(isinstance(character, dict) and character.get("id") for character in characters):
            raise CharacterCreationError("Unable to load characters.")
        return characters

    async def get(self, auth: dict, character_id: str) -> dict:
        try:
            envelope = await self.rabbit.request(
                MessageType.CHARACTER_GET, {"character_id": character_id}, timeout=self.timeout,
                provider=auth.get("provider"), provider_user_id=auth.get("provider_user_id"), user_id=auth.get("user_id"),
            )
        except Exception as exc:
            raise BackendUnavailableError(str(exc)) from exc
        payload = envelope.payload
        if not isinstance(payload, dict) or not payload.get("ok") or not isinstance(payload.get("character"), dict):
            raise CharacterCreationError((payload or {}).get("error", "Unable to load character."))
        return payload["character"]


def _list_keyboard(characters: list[dict]) -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text=character.get("name", "Unnamed"), callback_data=f"cm:view:{character['id']}")]
        for character in characters
    ] + [[InlineKeyboardButton(text="⬅️ Back", callback_data="menu:main")]])


async def handle_my_characters(message: Message, state, management_service: CharacterManagementService) -> None:
    auth = (await state.get_data()).get("auth")
    if not auth:
        await message.answer("Please /start the bot first.")
        return
    try:
        characters = await management_service.list(auth)
    except BackendUnavailableError:
        await message.answer(CHARACTER_UNAVAILABLE_TEXT)
        return
    except CharacterCreationError as exc:
        await message.answer(str(exc))
        return
    if not characters:
        await message.answer("You have no saved characters. Choose Create Character to begin.")
        return
    await state.update_data(managed_characters=characters)
    await message.answer("Choose a character:", reply_markup=_list_keyboard(characters))


async def handle_management_callback(callback: CallbackQuery, state, creation_service, management_service) -> None:
    await callback.answer()
    if not callback.message:
        return
    if callback.data == "cm:back":
        await callback.message.edit_text("Use the persistent menu below.")
        return
    if callback.data and callback.data.startswith("cm:view:"):
        character_id = callback.data.removeprefix("cm:view:")
        auth = (await state.get_data()).get("auth")
        if not auth:
            await callback.answer("Please /start the bot first.", show_alert=True)
            return
        try:
            character = await management_service.get(auth, character_id)
        except BackendUnavailableError:
            await callback.message.edit_text(CHARACTER_UNAVAILABLE_TEXT)
            return
        except CharacterCreationError as exc:
            await callback.message.edit_text(str(exc))
            return
        await state.update_data(selected_character=character)
        await callback.message.edit_text(
            sheet_text(character, "overview"),
            reply_markup=sheet_keyboard(character_id, "overview", page_count=sheet_page_count(character, "overview")),
        )
        return
    if callback.data and callback.data.startswith("cs:"):
        parts = callback.data.split(":")
        if len(parts) != 4 or parts[2] not in dict(SHEET_SECTIONS):
            await callback.answer("This sheet action has expired.", show_alert=True)
            return
        character_id, section = parts[1], parts[2]
        try:
            page = int(parts[3])
        except ValueError:
            await callback.answer("This sheet action has expired.", show_alert=True)
            return
        character = (await state.get_data()).get("selected_character")
        if not isinstance(character, dict) or str(character.get("id")) != character_id:
            await callback.answer("This character sheet has expired.", show_alert=True)
            return
        page_count = sheet_page_count(character, section)
        if page < 0 or page >= page_count:
            await callback.answer("This sheet page has expired.", show_alert=True)
            return
        await callback.message.edit_text(sheet_text(character, section, page), reply_markup=sheet_keyboard(character_id, section, page, page_count))
        return
    if callback.data and callback.data.startswith("cm:edit:"):
        character_id = callback.data.removeprefix("cm:edit:")
        auth = (await state.get_data()).get("auth")
        try:
            draft = await creation_service.start_edit(auth, character_id)
        except BackendUnavailableError:
            await callback.message.answer(CHARACTER_UNAVAILABLE_TEXT)
            return
        except CharacterCreationError as exc:
            await callback.message.answer(str(exc))
            return
        await state.clear()
        await state.update_data(auth=auth, draft_id=draft["id"], draft_data=draft.get("data") or {}, target_character_id=draft["target_character_id"])
        await state.set_state(CharacterCreationStates.summary)
        await callback.message.answer(_summary_text(await state.get_data()), reply_markup=navigation_keyboard())


def build_management_router() -> Router:
    router = Router(name="character_management")
    router.callback_query.register(handle_management_callback, F.data.startswith("cm:"))
    router.callback_query.register(handle_management_callback, F.data.startswith("cs:"))
    return router
