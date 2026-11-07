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
                provider=auth.get("provider"), provider_user_id=auth.get("provider_user_id"),
                user_id=auth.get("user_id"),
            )
        except Exception as exc:
            raise BackendUnavailableError(str(exc)) from exc
        payload = envelope.payload
        if not isinstance(payload, dict) or not payload.get("ok"):
            raise CharacterCreationError((payload or {}).get("error", "Unable to load characters."))
        characters = payload.get("characters", [])
        if not isinstance(characters, list) or not all(
            isinstance(character, dict) and character.get("id") for character in characters
        ):
            raise CharacterCreationError("Unable to load characters.")
        return characters


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


async def handle_management_callback(callback: CallbackQuery, state, creation_service) -> None:
    await callback.answer()
    if not callback.message:
        return
    if callback.data == "cm:back":
        await callback.message.answer("Use the persistent menu below.")
        return
    if callback.data and callback.data.startswith("cm:view:"):
        character_id = callback.data.removeprefix("cm:view:")
        characters = (await state.get_data()).get("managed_characters", [])
        character = next(
            (item for item in characters if str(item.get("id")) == character_id), None
        )
        if character is None:
            await callback.message.answer("This character is no longer available.")
            return
        await callback.message.answer(
            f"Name: {character.get('name', '-')}\n"
            f"Race: {character.get('kind', '-')}\n"
            f"Class: {character.get('spec_class', '-')}\n"
            f"Level: {character.get('level', '-')}\n\n"
            "Choose an action:",
            reply_markup=InlineKeyboardMarkup(inline_keyboard=[
                [InlineKeyboardButton(text="✏️ Edit Character", callback_data=f"cm:edit:{character_id}")],
                [InlineKeyboardButton(text="⬅️ Back", callback_data="cm:back")],
            ]),
        )
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
        draft_data = draft.get("data") or {}
        await state.clear()
        await state.update_data(
            auth=auth,
            draft_id=draft["id"],
            draft_data=draft_data,
            target_character_id=draft["target_character_id"],
        )
        await state.set_state(CharacterCreationStates.summary)
        await callback.message.answer(
            _summary_text(await state.get_data()), reply_markup=navigation_keyboard()
        )


def build_management_router() -> Router:
    router = Router(name="character_management")
    router.callback_query.register(handle_management_callback, F.data.startswith("cm:"))
    return router
