import asyncio
from types import SimpleNamespace
from unittest.mock import AsyncMock

from app.modules.backstory.keyboards import (
    backstory_edit_keyboard,
    backstory_hub_keyboard,
    backstory_prompt_keyboard,
    backstory_review_keyboard,
)
from app.modules.backstory.router import (
    MAX_BACKSTORY_LENGTH,
    MAX_PROMPT_LENGTH,
    build_backstory_router,
    handle_backstory_callback,
    handle_close,
    handle_edit_input,
    handle_hub_hint,
    handle_prompt_input,
    handle_review_hint,
)
from app.modules.backstory.states import BackstoryStates
from app.modules.character.service import (
    BackendUnavailableError,
    CharacterCreationError,
)
from app.utils.constants import (
    BACKSTORY_CLOSED_TEXT,
    BACKSTORY_DISCARDED_TEXT,
    BACKSTORY_EDIT_TEXT,
    BACKSTORY_GENERATING_TEXT,
    BACKSTORY_HUB_HINT_TEXT,
    BACKSTORY_NOT_STARTED_TEXT,
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

AUTH = {
    "provider": "telegram",
    "provider_user_id": "7",
    "user_id": "user-1",
    "username": "hero",
    "access_token": "token",
}


class FakeState:
    def __init__(self, data=None, state=None):
        self.data = dict(data or {})
        self._state = state

    @property
    def state(self):
        return self._state

    async def get_data(self):
        return dict(self.data)

    async def update_data(self, **kwargs):
        self.data.update(kwargs)

    async def set_state(self, state=None):
        self._state = None if state is None else state.state

    async def get_state(self):
        return self._state

    async def clear(self):
        self.data.clear()
        self._state = None


class FakeCreationService:
    def __init__(self):
        self.generated = []
        self.saved_backstories = []
        self.sequence = 0
        self.fail_with = None

    async def generate_backstory(self, auth, character_id, prompt=None):
        if self.fail_with is not None:
            raise self.fail_with
        self.generated.append((character_id, prompt))
        self.sequence += 1
        return f"Story version {self.sequence}."

    async def save_backstory(self, auth, character_id, backstory):
        if self.fail_with is not None:
            raise self.fail_with
        self.saved_backstories.append((character_id, backstory))
        return backstory


def _message(text=None):
    message = AsyncMock()
    message.text = text
    message.from_user = SimpleNamespace(id=7, username="hero", first_name="Hana")
    return message


def _callback(data):
    callback = AsyncMock()
    callback.data = data
    callback.message = AsyncMock()
    return callback


def _last_answer(mock):
    return mock.answer.call_args.args[0]


def _keyboard(mock):
    return mock.answer.call_args.kwargs["reply_markup"]


def _callback_data(markup):
    return [
        button.callback_data
        for row in markup.inline_keyboard
        for button in row
    ]


def _hub_state(data=None):
    merged = {"auth": dict(AUTH), "character_id": "char-1"}
    merged.update(data or {})
    return FakeState(
        data=merged, state=BackstoryStates.character_saved.state
    )


def _review_state(backstory="Story version 1.", state=None):
    return state or FakeState(
        data={"auth": dict(AUTH), "character_id": "char-1", "backstory": backstory},
        state=BackstoryStates.review.state,
    )


def test_start_from_hub_shows_prompt_options():
    state = _hub_state()
    service = FakeCreationService()
    callback = _callback("bs:start")

    asyncio.run(handle_backstory_callback(callback, state, service))

    assert state.state == BackstoryStates.prompt.state
    assert _last_answer(callback.message) == BACKSTORY_START_TEXT
    assert _callback_data(_keyboard(callback.message)) == _callback_data(
        backstory_prompt_keyboard()
    )


def test_start_without_character_id_alerts_not_started():
    state = FakeState(data={"auth": dict(AUTH)})
    service = FakeCreationService()
    callback = _callback("bs:start")

    asyncio.run(handle_backstory_callback(callback, state, service))

    assert state.state is None
    callback.answer.assert_awaited_with(
        BACKSTORY_NOT_STARTED_TEXT, show_alert=True
    )


def test_start_outside_hub_alerts_stale():
    state = _review_state()
    service = FakeCreationService()
    callback = _callback("bs:start")

    asyncio.run(handle_backstory_callback(callback, state, service))

    callback.answer.assert_awaited_with(CHARACTER_STALE_TEXT, show_alert=True)


def test_prompt_text_generates_backstory_and_shows_review():
    state = _hub_state()
    asyncio.run(handle_backstory_callback(_callback("bs:start"), state, FakeCreationService()))
    service = FakeCreationService()

    message = _message("  swears vengeance against the dragon  ")
    asyncio.run(handle_prompt_input(message, state, service))

    assert service.generated == [
        ("char-1", "swears vengeance against the dragon")
    ]
    assert state.state == BackstoryStates.review.state
    assert state.data["backstory"] == "Story version 1."
    assert state.data["backstory_prompt"] == "swears vengeance against the dragon"
    assert BACKSTORY_GENERATING_TEXT in message.answer.call_args_list[0].args[0]
    review_text = _last_answer(message)
    assert "Story version 1." in review_text
    assert _callback_data(_keyboard(message)) == _callback_data(
        backstory_review_keyboard()
    )


def test_generate_button_without_prompt_sends_none():
    state = _hub_state()
    asyncio.run(
        handle_backstory_callback(_callback("bs:start"), state, FakeCreationService())
    )
    service = FakeCreationService()

    callback = _callback("bs:gen")
    asyncio.run(handle_backstory_callback(callback, state, service))

    assert service.generated == [("char-1", None)]
    assert state.state == BackstoryStates.review.state


def test_generate_button_uses_stored_prompt():
    state = _hub_state({"backstory_prompt": "noble birth"})
    service = FakeCreationService()
    asyncio.run(handle_backstory_callback(_callback("bs:start"), state, service))

    asyncio.run(handle_backstory_callback(_callback("bs:gen"), state, service))

    assert service.generated == [("char-1", "noble birth")]


def test_generate_backend_rejection_keeps_prompt_state():
    state = _hub_state()
    asyncio.run(
        handle_backstory_callback(_callback("bs:start"), state, FakeCreationService())
    )
    service = FakeCreationService()
    service.fail_with = CharacterCreationError("Daily limit reached: 5/5")

    callback = _callback("bs:gen")
    asyncio.run(handle_backstory_callback(callback, state, service))

    assert state.state == BackstoryStates.prompt.state
    assert _last_answer(callback.message) == "Daily limit reached: 5/5"


def test_generate_backend_unavailable_keeps_prompt_state():
    state = _hub_state()
    asyncio.run(
        handle_backstory_callback(_callback("bs:start"), state, FakeCreationService())
    )
    service = FakeCreationService()
    service.fail_with = BackendUnavailableError("broker down")

    callback = _callback("bs:gen")
    asyncio.run(handle_backstory_callback(callback, state, service))

    assert state.state == BackstoryStates.prompt.state
    assert _last_answer(callback.message) == CHARACTER_UNAVAILABLE_TEXT


def test_prompt_input_without_context_replies_not_started():
    state = FakeState(data={"auth": dict(AUTH)})
    service = FakeCreationService()

    message = _message("something")
    asyncio.run(handle_prompt_input(message, state, service))

    assert service.generated == []
    assert _last_answer(message) == BACKSTORY_NOT_STARTED_TEXT


def test_prompt_empty_input_rejected():
    state = _hub_state()
    asyncio.run(
        handle_backstory_callback(_callback("bs:start"), state, FakeCreationService())
    )

    message = _message("   ")
    asyncio.run(handle_prompt_input(message, state, FakeCreationService()))

    assert state.state == BackstoryStates.prompt.state
    assert _last_answer(message) == CHARACTER_EMPTY_INPUT_TEXT


def test_prompt_input_too_long_rejected():
    state = _hub_state()
    asyncio.run(
        handle_backstory_callback(_callback("bs:start"), state, FakeCreationService())
    )

    message = _message("x" * (MAX_PROMPT_LENGTH + 1))
    asyncio.run(handle_prompt_input(message, state, FakeCreationService()))

    assert state.state == BackstoryStates.prompt.state
    assert _last_answer(message) == CHARACTER_TOO_LONG_TEXT


def test_accept_saves_backstory_and_returns_to_hub():
    state = _review_state("A wandering hero.")
    service = FakeCreationService()
    callback = _callback("bs:accept")

    asyncio.run(handle_backstory_callback(callback, state, service))

    assert service.saved_backstories == [("char-1", "A wandering hero.")]
    assert state.state == BackstoryStates.character_saved.state
    assert _last_answer(callback.message) == BACKSTORY_SAVED_TEXT
    assert _callback_data(_keyboard(callback.message)) == _callback_data(
        backstory_hub_keyboard()
    )


def test_accept_backend_rejection_keeps_review_state():
    state = _review_state()
    service = FakeCreationService()
    service.fail_with = CharacterCreationError("Backstory text is required.")
    callback = _callback("bs:accept")

    asyncio.run(handle_backstory_callback(callback, state, service))

    assert service.saved_backstories == []
    assert state.state == BackstoryStates.review.state
    assert _last_answer(callback.message) == "Backstory text is required."


def test_accept_backend_unavailable_keeps_review_state():
    state = _review_state()
    service = FakeCreationService()
    service.fail_with = BackendUnavailableError("broker down")
    callback = _callback("bs:accept")

    asyncio.run(handle_backstory_callback(callback, state, service))

    assert service.saved_backstories == []
    assert state.state == BackstoryStates.review.state
    assert _last_answer(callback.message) == CHARACTER_UNAVAILABLE_TEXT


def test_accept_without_backstory_in_state_alerts_stale():
    state = FakeState(
        data={"auth": dict(AUTH), "character_id": "char-1"},
        state=BackstoryStates.review.state,
    )
    service = FakeCreationService()
    callback = _callback("bs:accept")

    asyncio.run(handle_backstory_callback(callback, state, service))

    assert service.saved_backstories == []
    callback.answer.assert_awaited_with(CHARACTER_STALE_TEXT, show_alert=True)


def test_accept_outside_review_alerts_stale():
    state = _hub_state()
    service = FakeCreationService()
    callback = _callback("bs:accept")

    asyncio.run(handle_backstory_callback(callback, state, service))

    callback.answer.assert_awaited_with(CHARACTER_STALE_TEXT, show_alert=True)


def test_regenerate_produces_new_version_in_review():
    state = _review_state("Story version 1.")
    service = FakeCreationService()
    service.sequence = 1
    callback = _callback("bs:regen")

    asyncio.run(handle_backstory_callback(callback, state, service))

    assert service.generated == [("char-1", None)]
    assert state.state == BackstoryStates.review.state
    assert state.data["backstory"] == "Story version 2."
    assert "Story version 2." in _last_answer(callback.message)


def test_regenerate_outside_review_alerts_stale():
    state = _hub_state()
    service = FakeCreationService()
    callback = _callback("bs:regen")

    asyncio.run(handle_backstory_callback(callback, state, service))

    callback.answer.assert_awaited_with(CHARACTER_STALE_TEXT, show_alert=True)


def test_edit_moves_to_edit_state():
    state = _review_state("Story version 1.")
    service = FakeCreationService()
    callback = _callback("bs:edit")

    asyncio.run(handle_backstory_callback(callback, state, service))

    assert state.state == BackstoryStates.edit.state
    assert _last_answer(callback.message) == BACKSTORY_EDIT_TEXT
    assert _callback_data(_keyboard(callback.message)) == _callback_data(
        backstory_edit_keyboard()
    )


def test_edit_input_returns_to_review_with_new_text():
    state = _review_state("Story version 1.")
    asyncio.run(handle_backstory_callback(_callback("bs:edit"), state, FakeCreationService()))
    service = FakeCreationService()

    message = _message("Manually corrected backstory.")
    asyncio.run(handle_edit_input(message, state, service))

    assert state.state == BackstoryStates.review.state
    assert state.data["backstory"] == "Manually corrected backstory."
    assert "Manually corrected backstory." in _last_answer(message)


def test_edit_input_empty_rejected():
    state = _review_state("Story version 1.")
    asyncio.run(handle_backstory_callback(_callback("bs:edit"), state, FakeCreationService()))

    message = _message("  ")
    asyncio.run(handle_edit_input(message, state, FakeCreationService()))

    assert state.state == BackstoryStates.edit.state
    assert _last_answer(message) == CHARACTER_EMPTY_INPUT_TEXT


def test_edit_input_too_long_rejected():
    state = _review_state("Story version 1.")
    asyncio.run(handle_backstory_callback(_callback("bs:edit"), state, FakeCreationService()))

    message = _message("x" * (MAX_BACKSTORY_LENGTH + 1))
    asyncio.run(handle_edit_input(message, state, FakeCreationService()))

    assert state.state == BackstoryStates.edit.state
    assert _last_answer(message) == BACKSTORY_TOO_LONG_TEXT


def test_edit_input_without_context_replies_not_started():
    state = FakeState(data={"auth": dict(AUTH)})
    service = FakeCreationService()

    message = _message("text")
    asyncio.run(handle_edit_input(message, state, service))

    assert _last_answer(message) == BACKSTORY_NOT_STARTED_TEXT


def test_back_from_prompt_returns_to_hub():
    state = _hub_state()
    asyncio.run(
        handle_backstory_callback(_callback("bs:start"), state, FakeCreationService())
    )
    callback = _callback("bs:back")

    asyncio.run(handle_backstory_callback(callback, state, FakeCreationService()))

    assert state.state == BackstoryStates.character_saved.state
    assert _last_answer(callback.message) == CHARACTER_SAVED_TEXT


def test_back_from_edit_returns_to_review_with_previous_text():
    state = _review_state("Story version 1.")
    asyncio.run(handle_backstory_callback(_callback("bs:edit"), state, FakeCreationService()))
    callback = _callback("bs:back")

    asyncio.run(handle_backstory_callback(callback, state, FakeCreationService()))

    assert state.state == BackstoryStates.review.state
    assert "Story version 1." in _last_answer(callback.message)


def test_back_outside_prompt_or_edit_alerts_stale():
    state = _review_state()
    callback = _callback("bs:back")

    asyncio.run(handle_backstory_callback(callback, state, FakeCreationService()))

    callback.answer.assert_awaited_with(CHARACTER_STALE_TEXT, show_alert=True)


def test_cancel_from_review_discards_and_returns_to_hub():
    state = _review_state("Story version 1.")
    service = FakeCreationService()
    callback = _callback("bs:cancel")

    asyncio.run(handle_backstory_callback(callback, state, service))

    assert service.saved_backstories == []
    assert state.state == BackstoryStates.character_saved.state
    assert _last_answer(callback.message) == BACKSTORY_DISCARDED_TEXT
    assert _callback_data(_keyboard(callback.message)) == _callback_data(
        backstory_hub_keyboard()
    )


def test_cancel_from_prompt_returns_to_hub():
    state = _hub_state()
    asyncio.run(
        handle_backstory_callback(_callback("bs:start"), state, FakeCreationService())
    )
    callback = _callback("bs:cancel")

    asyncio.run(handle_backstory_callback(callback, state, FakeCreationService()))

    assert state.state == BackstoryStates.character_saved.state
    assert _last_answer(callback.message) == CHARACTER_SAVED_TEXT


def test_cancel_from_edit_returns_to_hub():
    state = _review_state("Story version 1.")
    asyncio.run(handle_backstory_callback(_callback("bs:edit"), state, FakeCreationService()))
    callback = _callback("bs:cancel")

    asyncio.run(handle_backstory_callback(callback, state, FakeCreationService()))

    assert state.state == BackstoryStates.character_saved.state


def test_cancel_outside_flow_alerts_stale():
    state = _hub_state()
    callback = _callback("bs:cancel")

    asyncio.run(handle_backstory_callback(callback, state, FakeCreationService()))

    callback.answer.assert_awaited_with(CHARACTER_STALE_TEXT, show_alert=True)


def test_close_clears_state_from_hub():
    state = _hub_state()
    service = FakeCreationService()
    callback = _callback("bs:close")

    asyncio.run(handle_backstory_callback(callback, state, service))

    assert state.state is None
    assert state.data == {}
    assert _last_answer(callback.message) == BACKSTORY_CLOSED_TEXT


def test_close_clears_state_from_review():
    state = _review_state()
    service = FakeCreationService()
    callback = _callback("bs:close")

    asyncio.run(handle_backstory_callback(callback, state, service))

    assert state.state is None
    assert state.data == {}
    assert service.saved_backstories == []
    assert _last_answer(callback.message) == BACKSTORY_CLOSED_TEXT


def test_close_outside_backstory_states_alerts_stale():
    state = FakeState(data={"auth": dict(AUTH), "character_id": "char-1"})
    callback = _callback("bs:close")

    asyncio.run(handle_backstory_callback(callback, state, FakeCreationService()))

    callback.answer.assert_awaited_with(CHARACTER_STALE_TEXT, show_alert=True)


def test_close_without_context_alerts_not_started():
    state = FakeState()
    callback = _callback("bs:close")

    asyncio.run(handle_backstory_callback(callback, state, FakeCreationService()))

    callback.answer.assert_awaited_with(
        BACKSTORY_NOT_STARTED_TEXT, show_alert=True
    )


def test_cancel_command_clears_state():
    state = _hub_state()

    message = _message()
    asyncio.run(handle_close(message, state))

    assert state.state is None
    assert state.data == {}
    assert _last_answer(message) == BACKSTORY_CLOSED_TEXT


def test_cancel_command_without_context_replies_not_started():
    state = FakeState()

    message = _message()
    asyncio.run(handle_close(message, state))

    assert _last_answer(message) == BACKSTORY_NOT_STARTED_TEXT


def test_free_text_in_review_shows_hint():
    state = _review_state()

    message = _message("hello")
    asyncio.run(handle_review_hint(message, state))

    assert _last_answer(message) == BACKSTORY_REVIEW_HINT_TEXT


def test_free_text_in_hub_shows_hint():
    state = _hub_state()

    message = _message("hello")
    asyncio.run(handle_hub_hint(message, state))

    assert _last_answer(message) == BACKSTORY_HUB_HINT_TEXT


def test_review_text_escapes_html():
    from app.modules.backstory.router import _review_text

    text = _review_text("Goblin <b>bane</b> & co")
    assert "&lt;b&gt;" in text
    assert "&amp;" in text


def test_full_flow_generate_accept_then_close():
    state = _hub_state()
    service = FakeCreationService()

    start = _callback("bs:start")
    asyncio.run(handle_backstory_callback(start, state, service))
    assert state.state == BackstoryStates.prompt.state

    prompt_message = _message("orphan raised by wolves")
    asyncio.run(handle_prompt_input(prompt_message, state, service))
    assert state.state == BackstoryStates.review.state

    accept = _callback("bs:accept")
    asyncio.run(handle_backstory_callback(accept, state, service))
    assert state.state == BackstoryStates.character_saved.state
    assert service.saved_backstories == [
        ("char-1", "Story version 1.")
    ]
    assert state.data["backstory_prompt"] == "orphan raised by wolves"

    close = _callback("bs:close")
    asyncio.run(handle_backstory_callback(close, state, service))
    assert state.state is None
    assert state.data == {}


def test_backstory_router_registers_expected_handlers():
    router = build_backstory_router()

    message_names = [
        handler.callback.__name__ for handler in router.message.handlers
    ]
    assert sorted(message_names) == sorted(
        [
            "handle_close",
            "handle_prompt_input",
            "handle_edit_input",
            "handle_review_hint",
            "handle_hub_hint",
        ]
    )
    callback_names = [
        handler.callback.__name__ for handler in router.callback_query.handlers
    ]
    assert callback_names == ["handle_backstory_callback"]
