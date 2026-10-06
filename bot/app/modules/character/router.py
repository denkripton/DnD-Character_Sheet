from aiogram import F, Router
from aiogram.filters import Command, StateFilter
from aiogram.types import CallbackQuery, InlineKeyboardMarkup, Message

from app.modules.character.keyboards import (
    CALLBACK_BACK,
    CALLBACK_CANCEL,
    CALLBACK_CONFIRM,
    CALLBACK_EDIT,
    CALLBACK_FULL_EDIT,
    CALLBACK_FULL_METHOD,
    CALLBACK_FULL_REGEN,
    CALLBACK_GEN_FULL,
    CALLBACK_GEN_STEP,
    CALLBACK_GENERATE,
    CALLBACK_MANUAL,
    CALLBACK_METHOD,
    CALLBACK_REGEN,
    CALLBACK_SET,
    generation_method_keyboard,
    generation_mode_keyboard,
    generation_result_keyboard,
    navigation_keyboard,
    stats_keyboard,
    stats_method_keyboard,
    step_keyboard,
)
from app.modules.character.service import (
    BackendUnavailableError,
    CharacterCreationError,
    CharacterCreationService,
)
from app.modules.character.states import CharacterCreationStates
from app.modules.character.steps import (
    STATS_ABBREVIATIONS,
    STATS_FIELDS,
    STATS_GENERATOR_METHODS,
    STATS_METHODS,
    STEPS,
    WizardStep,
    next_position,
    position_for_state,
    previous_position,
    prompt_for,
    state_for_position,
    stats_entry_prompt,
    stats_method_label,
    stats_method_prompt,
    step_for_position,
)
from app.utils.constants import (
    CHARACTER_AUTH_REQUIRED_TEXT,
    CHARACTER_CANCELLED_TEXT,
    CHARACTER_EMPTY_INPUT_TEXT,
    CHARACTER_FIRST_STEP_TEXT,
    CHARACTER_GENERATION_HINT_TEXT,
    CHARACTER_GENERATION_METHOD_TEXT,
    CHARACTER_GENERATION_MODE_TEXT,
    CHARACTER_IN_PROGRESS_TEXT,
    CHARACTER_MANUAL_HINT_TEXT,
    CHARACTER_NOT_STARTED_TEXT,
    CHARACTER_STALE_TEXT,
    CHARACTER_STATS_FORMAT_TEXT,
    CHARACTER_STATS_METHOD_HINT_TEXT,
    CHARACTER_STATS_NONE_TEXT,
    CHARACTER_SUMMARY_HINT_TEXT,
    CHARACTER_TOO_LONG_TEXT,
    CHARACTER_UNAVAILABLE_TEXT,
)

MAX_INPUT_LENGTH = 1000


def _modifier_text(modifier) -> str:
    if not isinstance(modifier, int) or isinstance(modifier, bool):
        return "-"
    return f"+{modifier}" if modifier >= 0 else str(modifier)


def _stats_lines(stats: dict, modifiers: dict) -> list[str]:
    lines = []
    for field in STATS_FIELDS:
        value = stats.get(field)
        if value is None:
            continue
        abbreviation = STATS_ABBREVIATIONS[field]
        modifier = _modifier_text(modifiers.get(field))
        lines.append(f"{abbreviation} {value} ({modifier})")
    return lines


def _stats_view_text(result: dict, method: str | None) -> str:
    stats = result.get("stats") or {}
    modifiers = result.get("modifiers") or {}
    lines = [f"Ability scores ({stats_method_label(method)}):"]
    lines.extend(_stats_lines(stats, modifiers))
    lines.append("")
    lines.append("Type six new values to edit, or use the buttons below.")
    return "\n".join(lines)


def _summary_text(data: dict) -> str:
    draft = data.get("draft_data") or {}
    name = draft.get("name") or "-"
    kind = draft.get("kind") or "-"
    spec_class = draft.get("spec_class") or "-"
    lines = [
        "Base identity is saved:",
        f"Name: {name}",
        f"Race: {kind}",
        f"Class: {spec_class}",
    ]
    result = data.get("stats_result")
    if isinstance(result, dict):
        stats = result.get("stats") or {}
        modifiers = result.get("modifiers") or {}
        lines.append("")
        lines.append(
            f"Ability scores ({stats_method_label(data.get('stats_method'))}):"
        )
        lines.extend(_stats_lines(stats, modifiers))
    lines.append("")
    lines.append(
        "The draft is stored on the server. "
        "Use /back to revise a value or /cancel to discard it."
    )
    return "\n".join(lines)


def _generation_result_text(data: dict) -> str:
    draft = data.get("draft_data") or {}
    lines = [
        "Your character has been generated:",
        f"Name: {draft.get('name') or '-'}",
        f"Race: {draft.get('kind') or '-'}",
        f"Class: {draft.get('spec_class') or '-'}",
        f"Alignment: {draft.get('alignment') or '-'}",
        f"Background: {draft.get('background') or '-'}",
    ]
    stats = data.get("stats") or {}
    modifiers = data.get("modifiers") or {}
    if stats:
        lines.append("")
        lines.append(
            f"Ability scores ({stats_method_label(data.get('stats_method'))}):"
        )
        lines.extend(_stats_lines(stats, modifiers))
    lines.append("")
    lines.append("Regenerate, edit any field, or /cancel to discard the draft.")
    return "\n".join(lines)


async def _base_context(state) -> tuple[dict, str] | None:
    data = await state.get_data()
    auth = data.get("auth")
    draft_id = data.get("draft_id")
    if not auth or not draft_id:
        return None
    return auth, draft_id


async def _wizard_context(state) -> tuple[dict, str, WizardStep] | None:
    base = await _base_context(state)
    if base is None:
        return None
    step = step_for_position(position_for_state(await state.get_state()))
    if step is None:
        return None
    auth, draft_id = base
    return auth, draft_id, step


async def _position_reply(
    state, position: str
) -> tuple[str, InlineKeyboardMarkup | None]:
    if position == "summary":
        return _summary_text(await state.get_data()), navigation_keyboard()
    step = step_for_position(position)
    if step is not None:
        return prompt_for(step), step_keyboard(step)
    if position == "stats_method":
        return stats_method_prompt(), stats_method_keyboard()
    data = await state.get_data()
    result = data.get("stats_result")
    method = data.get("stats_method")
    if isinstance(result, dict):
        return _stats_view_text(result, method), stats_keyboard(method, True)
    return stats_entry_prompt(), stats_keyboard(method, False)


async def _advance(target, state, step: WizardStep, draft: dict) -> None:
    await state.update_data(draft_data=draft.get("data") or {})
    position = next_position(step.position)
    if position is None or position == "summary":
        await state.set_state(state_for_position("summary"))
        await target.answer(
            _summary_text(await state.get_data()), reply_markup=navigation_keyboard()
        )
        return
    text, reply_markup = await _position_reply(state, position)
    await state.set_state(state_for_position(position))
    await target.answer(text, reply_markup=reply_markup)


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
    await state.set_state(CharacterCreationStates.generation_mode)
    await state.update_data(
        draft_id=draft.get("id"),
        draft_data=draft.get("data") or {},
        edit_from_generation=False,
    )
    await message.answer(
        CHARACTER_GENERATION_MODE_TEXT,
        reply_markup=generation_mode_keyboard(),
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


async def handle_stats_method_input(message: Message, state) -> None:
    await message.answer(CHARACTER_STATS_METHOD_HINT_TEXT)


async def handle_generation_hint(message: Message, state) -> None:
    await message.answer(CHARACTER_GENERATION_HINT_TEXT)


async def handle_stats_input(
    message: Message, state, creation_service: CharacterCreationService
) -> None:
    context = await _base_context(state)
    if context is None:
        await message.answer(CHARACTER_NOT_STARTED_TEXT)
        return
    auth, draft_id = context
    text = (message.text or "").strip()
    if not text:
        await message.answer(CHARACTER_EMPTY_INPUT_TEXT)
        return
    if len(text) > MAX_INPUT_LENGTH:
        await message.answer(CHARACTER_TOO_LONG_TEXT)
        return
    values = text.replace(",", " ").split()
    if len(values) != 6:
        await message.answer(CHARACTER_STATS_FORMAT_TEXT)
        return
    try:
        result = await creation_service.set_stats(auth, draft_id, values)
    except CharacterCreationError as exc:
        await message.answer(str(exc))
        return
    except BackendUnavailableError:
        await message.answer(CHARACTER_UNAVAILABLE_TEXT)
        return
    data = await state.get_data()
    method = data.get("stats_method")
    await state.update_data(stats_result=result)
    await message.answer(
        _stats_view_text(result, method),
        reply_markup=stats_keyboard(method, True),
    )


async def handle_summary_input(message: Message, state) -> None:
    await message.answer(CHARACTER_SUMMARY_HINT_TEXT)


async def _back_reply(state) -> tuple[str, InlineKeyboardMarkup | None]:
    data = await state.get_data()
    if not data.get("draft_id"):
        return CHARACTER_NOT_STARTED_TEXT, None
    current = await state.get_state()
    if current == CharacterCreationStates.generation_method.state:
        await state.set_state(CharacterCreationStates.generation_mode)
        return CHARACTER_GENERATION_MODE_TEXT, generation_mode_keyboard()
    if current == CharacterCreationStates.generation_result.state:
        await state.set_state(CharacterCreationStates.generation_method)
        return CHARACTER_GENERATION_METHOD_TEXT, generation_method_keyboard()
    position = position_for_state(current)
    if position is None:
        return CHARACTER_NOT_STARTED_TEXT, None
    if position == "name" and data.get("edit_from_generation"):
        await state.set_state(CharacterCreationStates.generation_result)
        return _generation_result_text(data), generation_result_keyboard()
    previous = previous_position(position)
    if previous is None:
        return CHARACTER_FIRST_STEP_TEXT, None
    text, reply_markup = await _position_reply(state, previous)
    await state.set_state(state_for_position(previous))
    return text, reply_markup


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


async def _start_full_generation(callback: CallbackQuery, state) -> None:
    data = await state.get_data()
    if not data.get("draft_id") or not data.get("auth"):
        await callback.answer(CHARACTER_NOT_STARTED_TEXT, show_alert=True)
        return
    if (await state.get_state()) != CharacterCreationStates.generation_mode.state:
        await callback.answer(CHARACTER_STALE_TEXT, show_alert=True)
        return
    await state.set_state(CharacterCreationStates.generation_method)
    await callback.answer()
    await callback.message.answer(
        CHARACTER_GENERATION_METHOD_TEXT,
        reply_markup=generation_method_keyboard(),
    )


async def _start_step_by_step(callback: CallbackQuery, state) -> None:
    data = await state.get_data()
    if not data.get("draft_id") or not data.get("auth"):
        await callback.answer(CHARACTER_NOT_STARTED_TEXT, show_alert=True)
        return
    if (await state.get_state()) != CharacterCreationStates.generation_mode.state:
        await callback.answer(CHARACTER_STALE_TEXT, show_alert=True)
        return
    first_step = STEPS[0]
    await state.update_data(edit_from_generation=False)
    await state.set_state(state_for_position(first_step.position))
    await callback.answer()
    await callback.message.answer(
        prompt_for(first_step), reply_markup=step_keyboard(first_step)
    )


async def _handle_full_generation(
    callback: CallbackQuery,
    state,
    creation_service: CharacterCreationService,
    method: str,
) -> None:
    data = await state.get_data()
    if not data.get("draft_id") or not data.get("auth"):
        await callback.answer(CHARACTER_NOT_STARTED_TEXT, show_alert=True)
        return
    current = await state.get_state()
    allowed_states = (
        CharacterCreationStates.generation_method.state,
        CharacterCreationStates.generation_result.state,
    )
    if current not in allowed_states:
        await callback.answer(CHARACTER_STALE_TEXT, show_alert=True)
        return
    if method not in STATS_GENERATOR_METHODS:
        await callback.answer(CHARACTER_STALE_TEXT, show_alert=True)
        return
    auth = data["auth"]
    draft_id = data["draft_id"]
    try:
        result = await creation_service.generate_character(auth, draft_id, method)
    except CharacterCreationError as exc:
        await callback.answer()
        await callback.message.answer(str(exc))
        return
    except BackendUnavailableError:
        await callback.answer()
        await callback.message.answer(CHARACTER_UNAVAILABLE_TEXT)
        return
    draft = result.get("draft") or {}
    await state.update_data(
        draft_data=draft.get("data") or {},
        stats_method=method,
        stats=result.get("stats"),
        modifiers=result.get("modifiers"),
        edit_from_generation=False,
    )
    await state.set_state(CharacterCreationStates.generation_result)
    await callback.answer()
    await callback.message.answer(
        _generation_result_text(await state.get_data()),
        reply_markup=generation_result_keyboard(),
    )


async def _start_field_editing(callback: CallbackQuery, state) -> None:
    data = await state.get_data()
    if not data.get("draft_id") or not data.get("auth"):
        await callback.answer(CHARACTER_NOT_STARTED_TEXT, show_alert=True)
        return
    if (
        await state.get_state()
    ) != CharacterCreationStates.generation_result.state:
        await callback.answer(CHARACTER_STALE_TEXT, show_alert=True)
        return
    first_step = STEPS[0]
    await state.update_data(edit_from_generation=True)
    await state.set_state(state_for_position(first_step.position))
    await callback.answer()
    await callback.message.answer(
        prompt_for(first_step), reply_markup=step_keyboard(first_step)
    )


async def _choose_method(
    callback: CallbackQuery,
    state,
    creation_service: CharacterCreationService,
    method: str,
) -> None:
    if method not in STATS_METHODS:
        await callback.answer(CHARACTER_STALE_TEXT, show_alert=True)
        return
    context = await _base_context(state)
    if context is None:
        await callback.answer(CHARACTER_NOT_STARTED_TEXT, show_alert=True)
        return
    if position_for_state(await state.get_state()) != "stats_method":
        await callback.answer(CHARACTER_STALE_TEXT, show_alert=True)
        return
    auth, draft_id = context
    if method == "manual":
        await state.update_data(stats_method="manual")
        await state.set_state(state_for_position("stats"))
        text, reply_markup = await _position_reply(state, "stats")
        await callback.answer()
        await callback.message.answer(text, reply_markup=reply_markup)
        return
    try:
        result = await creation_service.generate_stats(auth, draft_id, method)
    except CharacterCreationError as exc:
        await callback.answer()
        await callback.message.answer(str(exc))
        return
    except BackendUnavailableError:
        await callback.answer()
        await callback.message.answer(CHARACTER_UNAVAILABLE_TEXT)
        return
    await state.update_data(stats_method=method, stats_result=result)
    await state.set_state(state_for_position("stats"))
    await callback.answer()
    await callback.message.answer(
        _stats_view_text(result, method), reply_markup=stats_keyboard(method, True)
    )


async def _regenerate(
    callback: CallbackQuery,
    state,
    creation_service: CharacterCreationService,
) -> None:
    context = await _base_context(state)
    if context is None:
        await callback.answer(CHARACTER_NOT_STARTED_TEXT, show_alert=True)
        return
    if position_for_state(await state.get_state()) != "stats":
        await callback.answer(CHARACTER_STALE_TEXT, show_alert=True)
        return
    data = await state.get_data()
    method = data.get("stats_method")
    if method not in STATS_GENERATOR_METHODS:
        await callback.answer(CHARACTER_STALE_TEXT, show_alert=True)
        return
    auth, draft_id = context
    try:
        result = await creation_service.generate_stats(auth, draft_id, method)
    except CharacterCreationError as exc:
        await callback.answer()
        await callback.message.answer(str(exc))
        return
    except BackendUnavailableError:
        await callback.answer()
        await callback.message.answer(CHARACTER_UNAVAILABLE_TEXT)
        return
    await state.update_data(stats_result=result)
    await callback.answer()
    await callback.message.answer(
        _stats_view_text(result, method), reply_markup=stats_keyboard(method, True)
    )


async def _edit_values(callback: CallbackQuery, state) -> None:
    data = await state.get_data()
    if position_for_state(await state.get_state()) != "stats" or not data.get("draft_id"):
        await callback.answer(CHARACTER_STALE_TEXT, show_alert=True)
        return
    await callback.answer()
    await callback.message.answer(
        stats_entry_prompt(),
        reply_markup=stats_keyboard(
            data.get("stats_method"), bool(data.get("stats_result"))
        ),
    )


async def _confirm_stats(callback: CallbackQuery, state) -> None:
    data = await state.get_data()
    if not data.get("draft_id") or not data.get("auth"):
        await callback.answer(CHARACTER_NOT_STARTED_TEXT, show_alert=True)
        return
    if position_for_state(await state.get_state()) != "stats":
        await callback.answer(CHARACTER_STALE_TEXT, show_alert=True)
        return
    if not isinstance(data.get("stats_result"), dict):
        await callback.answer(CHARACTER_STATS_NONE_TEXT, show_alert=True)
        return
    await state.set_state(state_for_position("summary"))
    await callback.answer()
    await callback.message.answer(
        _summary_text(data), reply_markup=navigation_keyboard()
    )


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
    if raw == CALLBACK_GEN_FULL:
        await _start_full_generation(callback, state)
        return
    if raw == CALLBACK_GEN_STEP:
        await _start_step_by_step(callback, state)
        return
    if raw.startswith(f"{CALLBACK_FULL_METHOD}:"):
        method = raw.removeprefix(f"{CALLBACK_FULL_METHOD}:")
        await _handle_full_generation(callback, state, creation_service, method)
        return
    if raw == CALLBACK_FULL_REGEN:
        data = await state.get_data()
        method = data.get("stats_method")
        await _handle_full_generation(callback, state, creation_service, method)
        return
    if raw == CALLBACK_FULL_EDIT:
        await _start_field_editing(callback, state)
        return
    if raw.startswith(f"{CALLBACK_METHOD}:"):
        method = raw.removeprefix(f"{CALLBACK_METHOD}:")
        await _choose_method(callback, state, creation_service, method)
        return
    if raw == CALLBACK_REGEN:
        await _regenerate(callback, state, creation_service)
        return
    if raw == CALLBACK_CONFIRM:
        await _confirm_stats(callback, state)
        return
    if raw == CALLBACK_EDIT:
        await _edit_values(callback, state)
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
        handle_generation_hint,
        StateFilter(
            CharacterCreationStates.generation_mode,
            CharacterCreationStates.generation_method,
            CharacterCreationStates.generation_result,
        ),
    )
    router.message.register(
        handle_stats_method_input, CharacterCreationStates.stats_method
    )
    router.message.register(
        handle_stats_input, CharacterCreationStates.stats
    )
    router.message.register(
        handle_summary_input, CharacterCreationStates.summary
    )
    router.callback_query.register(handle_callback, F.data.startswith("cc:"))
    return router


character_creation_router = build_character_creation_router()
