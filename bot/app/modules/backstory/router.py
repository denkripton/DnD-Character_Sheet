from html import escape

from aiogram import F, Router
from aiogram.filters import Command, StateFilter
from aiogram.types import CallbackQuery, Message

from app.modules.backstory.keyboards import (
    CALLBACK_ACCEPT,
    CALLBACK_BACK,
    CALLBACK_CANCEL,
    CALLBACK_CLOSE,
    CALLBACK_EDIT,
    CALLBACK_GENERATE,
    CALLBACK_MODEL,
    CALLBACK_MODELS,
    CALLBACK_REGENERATE,
    CALLBACK_START,
    backstory_edit_keyboard,
    backstory_hub_keyboard,
    backstory_model_keyboard,
    backstory_prompt_keyboard,
    backstory_review_keyboard,
)
from app.modules.backstory.states import BackstoryStates
from app.modules.character.service import (
    BackendUnavailableError,
    CharacterCreationError,
    CharacterCreationService,
)
from app.utils.constants import (
    BACKSTORY_CLOSED_TEXT,
    BACKSTORY_DISCARDED_TEXT,
    BACKSTORY_EDIT_TEXT,
    BACKSTORY_GENERATING_TEXT,
    BACKSTORY_HUB_HINT_TEXT,
    BACKSTORY_NOT_STARTED_TEXT,
    BACKSTORY_REVIEW_ACTIONS,
    BACKSTORY_REVIEW_HEADER,
    BACKSTORY_REVIEW_HINT_TEXT,
    BACKSTORY_SAVED_TEXT,
    BACKSTORY_START_TEXT,
    BACKSTORY_TOO_LONG_TEXT,
    CHARACTER_EMPTY_INPUT_TEXT,
    CHARACTER_SAVED_TEXT,
    CHARACTER_STALE_TEXT,
    CHARACTER_TOO_LONG_TEXT,
    CHARACTER_UNAVAILABLE_TEXT,
)

MAX_PROMPT_LENGTH = 1000
MAX_BACKSTORY_LENGTH = 10000

BACKSTORY_STATES = (
    BackstoryStates.character_saved,
    BackstoryStates.prompt,
    BackstoryStates.model_selection,
    BackstoryStates.review,
    BackstoryStates.edit,
)


async def _context(state) -> tuple[dict, str] | None:
    data = await state.get_data()
    auth = data.get("auth")
    character_id = data.get("character_id")
    if not auth or not character_id:
        return None
    return auth, character_id


def _review_text(backstory: str) -> str:
    return (
        f"{BACKSTORY_REVIEW_HEADER}\n\n{escape(backstory)}\n\n"
        f"{BACKSTORY_REVIEW_ACTIONS}"
    )


async def _show_hub(target, state) -> None:
    await state.set_state(BackstoryStates.character_saved)
    await target.answer(
        CHARACTER_SAVED_TEXT, reply_markup=backstory_hub_keyboard()
    )


async def _show_review(target, state, backstory: str) -> None:
    await state.update_data(backstory=backstory)
    await state.set_state(BackstoryStates.review)
    await target.answer(
        _review_text(backstory), reply_markup=backstory_review_keyboard()
    )


async def _generate(
    target, state, creation_service: CharacterCreationService
) -> None:
    context = await _context(state)
    if context is None:
        await target.answer(BACKSTORY_NOT_STARTED_TEXT)
        return
    auth, character_id = context
    data = await state.get_data()
    model = data.get("ai_model")
    provider = data.get("ai_provider")
    await target.answer(BACKSTORY_GENERATING_TEXT)
    try:
        backstory = await creation_service.generate_backstory(
            auth,
            character_id,
            prompt=data.get("backstory_prompt"),
            model=model,
            provider=provider,
        )
    except CharacterCreationError as exc:
        await target.answer(str(exc))
        return
    except BackendUnavailableError:
        await target.answer(CHARACTER_UNAVAILABLE_TEXT)
        return
    await _show_review(target, state, backstory)


async def handle_prompt_input(
    message: Message, state, creation_service: CharacterCreationService
) -> None:
    if await _context(state) is None:
        await message.answer(BACKSTORY_NOT_STARTED_TEXT)
        return
    text = (message.text or "").strip()
    if not text:
        await message.answer(CHARACTER_EMPTY_INPUT_TEXT)
        return
    if len(text) > MAX_PROMPT_LENGTH:
        await message.answer(CHARACTER_TOO_LONG_TEXT)
        return
    await state.update_data(backstory_prompt=text)
    await _generate(message, state, creation_service)


async def handle_edit_input(
    message: Message, state, creation_service: CharacterCreationService
) -> None:
    if await _context(state) is None:
        await message.answer(BACKSTORY_NOT_STARTED_TEXT)
        return
    text = (message.text or "").strip()
    if not text:
        await message.answer(CHARACTER_EMPTY_INPUT_TEXT)
        return
    if len(text) > MAX_BACKSTORY_LENGTH:
        await message.answer(BACKSTORY_TOO_LONG_TEXT)
        return
    await _show_review(message, state, text)


async def handle_hub_hint(message: Message, state) -> None:
    await message.answer(BACKSTORY_HUB_HINT_TEXT)


async def handle_review_hint(message: Message, state) -> None:
    await message.answer(BACKSTORY_REVIEW_HINT_TEXT)


async def handle_close(message: Message, state) -> None:
    data = await state.get_data()
    if not data.get("auth") and not data.get("character_id"):
        await message.answer(BACKSTORY_NOT_STARTED_TEXT)
        return
    await state.clear()
    await message.answer(BACKSTORY_CLOSED_TEXT)


async def _start_flow(callback: CallbackQuery, state) -> None:
    if await _context(state) is None:
        await callback.answer(BACKSTORY_NOT_STARTED_TEXT, show_alert=True)
        return
    if (
        await state.get_state()
    ) != BackstoryStates.character_saved.state:
        await callback.answer(CHARACTER_STALE_TEXT, show_alert=True)
        return
    await state.set_state(BackstoryStates.prompt)
    await callback.answer()
    await callback.message.answer(
        BACKSTORY_START_TEXT, reply_markup=backstory_prompt_keyboard()
    )


async def _generate_from_prompt(
    callback: CallbackQuery, state, creation_service: CharacterCreationService
) -> None:
    if await _context(state) is None:
        await callback.answer(BACKSTORY_NOT_STARTED_TEXT, show_alert=True)
        return
    if (await state.get_state()) != BackstoryStates.prompt.state:
        await callback.answer(CHARACTER_STALE_TEXT, show_alert=True)
        return
    await callback.answer()
    await _generate(callback.message, state, creation_service)


async def _regenerate(
    callback: CallbackQuery, state, creation_service: CharacterCreationService
) -> None:
    if await _context(state) is None:
        await callback.answer(BACKSTORY_NOT_STARTED_TEXT, show_alert=True)
        return
    if (await state.get_state()) != BackstoryStates.review.state:
        await callback.answer(CHARACTER_STALE_TEXT, show_alert=True)
        return
    await callback.answer()
    await _generate(callback.message, state, creation_service)


async def _accept(
    callback: CallbackQuery, state, creation_service: CharacterCreationService
) -> None:
    context = await _context(state)
    if context is None:
        await callback.answer(BACKSTORY_NOT_STARTED_TEXT, show_alert=True)
        return
    if (await state.get_state()) != BackstoryStates.review.state:
        await callback.answer(CHARACTER_STALE_TEXT, show_alert=True)
        return
    data = await state.get_data()
    backstory = data.get("backstory")
    if not isinstance(backstory, str) or not backstory:
        await callback.answer(CHARACTER_STALE_TEXT, show_alert=True)
        return
    auth, character_id = context
    try:
        await creation_service.save_backstory(auth, character_id, backstory)
    except CharacterCreationError as exc:
        await callback.answer()
        await callback.message.answer(str(exc))
        return
    except BackendUnavailableError:
        await callback.answer()
        await callback.message.answer(CHARACTER_UNAVAILABLE_TEXT)
        return
    await callback.answer()
    await callback.message.answer(
        BACKSTORY_SAVED_TEXT, reply_markup=backstory_hub_keyboard()
    )
    await state.set_state(BackstoryStates.character_saved)


async def _start_editing(callback: CallbackQuery, state) -> None:
    if await _context(state) is None:
        await callback.answer(BACKSTORY_NOT_STARTED_TEXT, show_alert=True)
        return
    if (await state.get_state()) != BackstoryStates.review.state:
        await callback.answer(CHARACTER_STALE_TEXT, show_alert=True)
        return
    await state.set_state(BackstoryStates.edit)
    await callback.answer()
    await callback.message.answer(
        BACKSTORY_EDIT_TEXT, reply_markup=backstory_edit_keyboard()
    )


async def _cancel(callback: CallbackQuery, state) -> None:
    if await _context(state) is None:
        await callback.answer(BACKSTORY_NOT_STARTED_TEXT, show_alert=True)
        return
    current = await state.get_state()
    if current not in (
        BackstoryStates.prompt.state,
        BackstoryStates.model_selection.state,
        BackstoryStates.review.state,
        BackstoryStates.edit.state,
    ):
        await callback.answer(CHARACTER_STALE_TEXT, show_alert=True)
        return
    await callback.answer()
    if current == BackstoryStates.review.state:
        await state.set_state(BackstoryStates.character_saved)
        await callback.message.answer(
            BACKSTORY_DISCARDED_TEXT, reply_markup=backstory_hub_keyboard()
        )
        return
    await _show_hub(callback.message, state)


async def _back(callback: CallbackQuery, state) -> None:
    if await _context(state) is None:
        await callback.answer(BACKSTORY_NOT_STARTED_TEXT, show_alert=True)
        return
    current = await state.get_state()
    if current == BackstoryStates.model_selection.state:
        data = await state.get_data()
        return_state = data.get("model_selection_return_state")
        if return_state not in (
            BackstoryStates.prompt.state,
            BackstoryStates.review.state,
        ):
            await callback.answer(CHARACTER_STALE_TEXT, show_alert=True)
            return
        await state.set_state(return_state)
        await callback.answer()
        keyboard = (
            backstory_prompt_keyboard()
            if return_state == BackstoryStates.prompt.state
            else backstory_review_keyboard()
        )
        await callback.message.answer("Choose an AI model.", reply_markup=keyboard)
        return
    if current == BackstoryStates.prompt.state:
        await callback.answer()
        await _show_hub(callback.message, state)
        return
    if current == BackstoryStates.edit.state:
        data = await state.get_data()
        backstory = data.get("backstory")
        if not isinstance(backstory, str) or not backstory:
            await callback.answer(CHARACTER_STALE_TEXT, show_alert=True)
            return
        await callback.answer()
        await state.set_state(BackstoryStates.review)
        await callback.message.answer(
            _review_text(backstory), reply_markup=backstory_review_keyboard()
        )
        return
    await callback.answer(CHARACTER_STALE_TEXT, show_alert=True)


async def _show_models(
    callback: CallbackQuery,
    state,
    creation_service: CharacterCreationService,
) -> None:
    context = await _context(state)
    current = await state.get_state()
    if context is None:
        await callback.answer(BACKSTORY_NOT_STARTED_TEXT, show_alert=True)
        return
    if current not in (
        BackstoryStates.prompt.state,
        BackstoryStates.review.state,
    ):
        await callback.answer(CHARACTER_STALE_TEXT, show_alert=True)
        return
    auth, _ = context
    try:
        providers = await creation_service.get_ai_catalog(auth)
    except CharacterCreationError as exc:
        await callback.answer()
        await callback.message.answer(str(exc))
        return
    except BackendUnavailableError:
        await callback.answer()
        await callback.message.answer(CHARACTER_UNAVAILABLE_TEXT)
        return
    if not any(provider["models"] for provider in providers):
        await callback.answer()
        await callback.message.answer("No AI models are currently available.")
        return
    await state.update_data(
        ai_catalog=providers,
        model_selection_return_state=current,
    )
    await state.set_state(BackstoryStates.model_selection)
    await callback.answer()
    await callback.message.answer(
        "Choose an available AI model.",
        reply_markup=backstory_model_keyboard(providers),
    )


async def _select_model(callback: CallbackQuery, state) -> None:
    raw = callback.data or ""
    parts = raw.split(":", 3)
    if (
        len(parts) != 4
        or (await state.get_state()) != BackstoryStates.model_selection.state
    ):
        await callback.answer(CHARACTER_STALE_TEXT, show_alert=True)
        return
    _, _, provider_name, model_name = parts
    state_data = await state.get_data()
    catalog = state_data.get("ai_catalog") or []
    available = any(
        provider.get("name") == provider_name
        and model_name in provider.get("models", [])
        for provider in catalog
        if isinstance(provider, dict)
    )
    return_state = state_data.get("model_selection_return_state")
    if not available or return_state not in (
        BackstoryStates.prompt.state,
        BackstoryStates.review.state,
    ):
        await callback.answer(CHARACTER_STALE_TEXT, show_alert=True)
        return
    await state.update_data(ai_provider=provider_name, ai_model=model_name)
    await state.set_state(return_state)
    await callback.answer()
    keyboard = (
        backstory_prompt_keyboard()
        if return_state == BackstoryStates.prompt.state
        else backstory_review_keyboard()
    )
    await callback.message.answer(
        f"AI model selected: {model_name} ({provider_name}).",
        reply_markup=keyboard,
    )


async def _close(callback: CallbackQuery, state) -> None:
    if await _context(state) is None:
        await callback.answer(BACKSTORY_NOT_STARTED_TEXT, show_alert=True)
        return
    if (await state.get_state()) not in tuple(
        item.state for item in BACKSTORY_STATES
    ):
        await callback.answer(CHARACTER_STALE_TEXT, show_alert=True)
        return
    await callback.answer()
    await state.clear()
    await callback.message.answer(BACKSTORY_CLOSED_TEXT)


async def handle_backstory_callback(
    callback: CallbackQuery, state, creation_service: CharacterCreationService
) -> None:
    raw = callback.data or ""
    if raw == CALLBACK_MODELS:
        await _show_models(callback, state, creation_service)
        return
    if raw.startswith(f"{CALLBACK_MODEL}:"):
        await _select_model(callback, state)
        return
    if raw == CALLBACK_START:
        await _start_flow(callback, state)
        return
    if raw == CALLBACK_GENERATE:
        await _generate_from_prompt(callback, state, creation_service)
        return
    if raw == CALLBACK_REGENERATE:
        await _regenerate(callback, state, creation_service)
        return
    if raw == CALLBACK_ACCEPT:
        await _accept(callback, state, creation_service)
        return
    if raw == CALLBACK_EDIT:
        await _start_editing(callback, state)
        return
    if raw == CALLBACK_CANCEL:
        await _cancel(callback, state)
        return
    if raw == CALLBACK_BACK:
        await _back(callback, state)
        return
    if raw == CALLBACK_CLOSE:
        await _close(callback, state)
        return


def build_backstory_router() -> Router:
    router = Router(name="backstory")
    router.message.register(
        handle_close,
        Command("cancel"),
        StateFilter(*BACKSTORY_STATES),
    )
    router.message.register(
        handle_prompt_input, BackstoryStates.prompt
    )
    router.message.register(handle_edit_input, BackstoryStates.edit)
    router.message.register(handle_review_hint, BackstoryStates.review)
    router.message.register(
        handle_hub_hint, BackstoryStates.character_saved
    )
    router.callback_query.register(
        handle_backstory_callback, F.data.startswith("bs:")
    )
    return router


backstory_router = build_backstory_router()
