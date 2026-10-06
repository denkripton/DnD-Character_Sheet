from aiogram import F, Router
from aiogram.filters import Command, StateFilter
from aiogram.types import CallbackQuery, InlineKeyboardMarkup, Message

from app.modules.character.keyboards import (
    CALLBACK_BACK,
    CALLBACK_CANCEL,
    CALLBACK_GENERATE,
    CALLBACK_MANUAL,
    CALLBACK_SET,
    navigation_keyboard,
    step_keyboard,
)
from app.modules.character.service import (
    BackendUnavailableError,
    CharacterCreationError,
    CharacterCreationService,
)
from app.modules.character.states import CharacterCreationStates
from app.modules.character.steps import (
    STEPS,
    WizardStep,
    next_position,
    position_for_state,
    previous_position,
    prompt_for,
    state_for_position,
    step_for_position,
)
from app.utils.constants import (
    CHARACTER_AUTH_REQUIRED_TEXT,
    CHARACTER_CANCELLED_TEXT,
    CHARACTER_EMPTY_INPUT_TEXT,
    CHARACTER_FIRST_STEP_TEXT,
    CHARACTER_IN_PROGRESS_TEXT,
    CHARACTER_MANUAL_HINT_TEXT,
    CHARACTER_NOT_STARTED_TEXT,
    CHARACTER_STALE_TEXT,
    CHARACTER_SUMMARY_HINT_TEXT,
    CHARACTER_TOO_LONG_TEXT,
    CHARACTER_UNAVAILABLE_TEXT,
)

MAX_INPUT_LENGTH = 1000


def _summary_text(draft: dict) -> str:
    data = draft.get("data") or {}
    name = data.get("name") or "-"
    kind = data.get("kind") or "-"
    spec_class = data.get("spec_class") or "-"
    return (
        "Base identity is saved:\n"
        f"Name: {name}\n"
        f"Race: {kind}\n"
        f"Class: {spec_class}\n\n"
        "The draft is stored on the server. "
        "Use /back to revise a value or /cancel to discard it."
    )


async def _wizard_context(state) -> tuple[dict, str, WizardStep] | None:
    data = await state.get_data()
    auth = data.get("auth")
    draft_id = data.get("draft_id")
    step = step_for_position(position_for_state(state.state))
    if not auth or not draft_id or step is None:
        return None
    return auth, draft_id, step


async def _advance(target, state, step: WizardStep, draft: dict) -> None:
    position = next_position(step.position)
    next_step = step_for_position(position)
    if position is None or next_step is None:
        await state.set_state(state_for_position("summary"))
        await target.answer(_summary_text(draft), reply_markup=navigation_keyboard())
        return
    await state.set_state(state_for_position(position))
    await target.answer(
        prompt_for(next_step), reply_markup=step_keyboard(next_step)
    )


async def _submit_value(
    target,
    state,
    creation_service: CharacterCreationService,
    auth: dict,
    draft_id: str,
    step: WizardStep,
    value: str,
) -> None:
    try:
        draft = await creation_service.set_value(
            auth, draft_id, step.field, value
        )
    except CharacterCreationError as exc:
        await target.answer(str(exc))
        return
    except BackendUnavailableError:
        await target.answer(CHARACTER_UNAVAILABLE_TEXT)
        return
    await _advance(target, state, step, draft)


async def _generate_value(
    target,
    state,
    creation_service: CharacterCreationService,
    auth: dict,
    draft_id: str,
    step: WizardStep,
) -> None:
    try:
        draft = await creation_service.generate_value(auth, draft_id, step.field)
    except CharacterCreationError as exc:
        await target.answer(str(exc))
        return
    except BackendUnavailableError:
        await target.answer(CHARACTER_UNAVAILABLE_TEXT)
        return
    await _advance(target, state, step, draft)


async def handle_create(
    message: Message, state, creation_service: CharacterCreationService
) -> None:
    data = await state.get_data()
    auth = data.get("auth")
    if not auth:
        await message.answer(CHARACTER_AUTH_REQUIRED_TEXT)
        return
    if data.get("draft_id"):
        await message.answer(CHARACTER_IN_PROGRESS_TEXT)
        return
    try:
        draft = await creation_service.start(auth)
    except CharacterCreationError as exc:
        await message.answer(str(exc))
        return
    except BackendUnavailableError:
        await message.answer(CHARACTER_UNAVAILABLE_TEXT)
        return
    first_step = STEPS[0]
    await state.set_state(state_for_position(first_step.position))
    await state.update_data(draft_id=draft.get("id"))
    await message.answer(
        prompt_for(first_step), reply_markup=step_keyboard(first_step)
    )


async def handle_step_input(
    message: Message, state, creation_service: CharacterCreationService
) -> None:
    context = await _wizard_context(state)
    if context is None:
        await message.answer(CHARACTER_NOT_STARTED_TEXT)
        return
    auth, draft_id, step = context
    text = (message.text or "").strip()
    if not text:
        await message.answer(CHARACTER_EMPTY_INPUT_TEXT)
        return
    if len(text) > MAX_INPUT_LENGTH:
        await message.answer(CHARACTER_TOO_LONG_TEXT)
        return
    await _submit_value(message, state, creation_service, auth, draft_id, step, text)


async def handle_summary_input(message: Message, state) -> None:
    await message.answer(CHARACTER_SUMMARY_HINT_TEXT)


async def _back_reply(state) -> tuple[str, InlineKeyboardMarkup | None]:
    data = await state.get_data()
    if not data.get("draft_id"):
        return CHARACTER_NOT_STARTED_TEXT, None
    position = position_for_state(state.state)
    if position is None:
        return CHARACTER_NOT_STARTED_TEXT, None
    previous = previous_position(position)
    if previous is None:
        return CHARACTER_FIRST_STEP_TEXT, None
    previous_step = step_for_position(previous)
    if previous_step is None:
        return CHARACTER_FIRST_STEP_TEXT, None
    await state.set_state(state_for_position(previous))
    return prompt_for(previous_step), step_keyboard(previous_step)


async def handle_back(message: Message, state) -> None:
    text, reply_markup = await _back_reply(state)
    await message.answer(text, reply_markup=reply_markup)


async def _cancel(
    target, state, creation_service: CharacterCreationService
) -> None:
    data = await state.get_data()
    auth = data.get("auth")
    draft_id = data.get("draft_id")
    if not draft_id:
        await target.answer(CHARACTER_NOT_STARTED_TEXT)
        return
    try:
        await creation_service.cancel(auth, draft_id)
    except CharacterCreationError:
        pass
    except BackendUnavailableError:
        await target.answer(CHARACTER_UNAVAILABLE_TEXT)
        return
    await state.clear()
    await target.answer(CHARACTER_CANCELLED_TEXT)


async def handle_cancel(
    message: Message, state, creation_service: CharacterCreationService
) -> None:
    await _cancel(message, state, creation_service)


async def handle_callback(
    callback: CallbackQuery, state, creation_service: CharacterCreationService
) -> None:
    raw = callback.data or ""
    if raw == CALLBACK_BACK:
        await callback.answer()
        text, reply_markup = await _back_reply(state)
        await callback.message.answer(text, reply_markup=reply_markup)
        return
    if raw == CALLBACK_CANCEL:
        await callback.answer()
        await _cancel(callback.message, state, creation_service)
        return
    if raw.startswith(f"{CALLBACK_MANUAL}:"):
        await callback.answer(CHARACTER_MANUAL_HINT_TEXT)
        return

    context = await _wizard_context(state)
    if context is None:
        data = await state.get_data()
        notice = (
            CHARACTER_STALE_TEXT
            if data.get("draft_id")
            else CHARACTER_NOT_STARTED_TEXT
        )
        await callback.answer(notice, show_alert=True)
        return
    auth, draft_id, step = context

    if raw.startswith(f"{CALLBACK_SET}:"):
        _, _, position, value = raw.split(":", 3)
        if position != step.position:
            await callback.answer(CHARACTER_STALE_TEXT, show_alert=True)
            return
        await callback.answer()
        await _submit_value(
            callback.message, state, creation_service, auth, draft_id, step, value
        )
        return
    if raw.startswith(f"{CALLBACK_GENERATE}:"):
        position = raw.removeprefix(f"{CALLBACK_GENERATE}:")
        if position != step.position:
            await callback.answer(CHARACTER_STALE_TEXT, show_alert=True)
            return
        await callback.answer()
        await _generate_value(
            callback.message, state, creation_service, auth, draft_id, step
        )
        return
    await callback.answer(CHARACTER_STALE_TEXT, show_alert=True)


def build_character_creation_router() -> Router:
    router = Router(name="character_creation")
    router.message.register(
        handle_create, Command("create_character", "create")
    )
    router.message.register(handle_back, Command("back"))
    router.message.register(handle_cancel, Command("cancel"))
    router.message.register(
        handle_step_input,
        StateFilter(
            CharacterCreationStates.name,
            CharacterCreationStates.race,
            CharacterCreationStates.spec_class,
        ),
    )
    router.message.register(
        handle_summary_input, CharacterCreationStates.summary
    )
    router.callback_query.register(handle_callback, F.data.startswith("cc:"))
    return router


character_creation_router = build_character_creation_router()
