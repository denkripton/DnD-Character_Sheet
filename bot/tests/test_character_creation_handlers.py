import asyncio
from types import SimpleNamespace
from unittest.mock import AsyncMock

from app.modules.character.keyboards import (
    CALLBACK_BACK,
    CALLBACK_CANCEL,
    step_keyboard,
)
from app.modules.character.router import (
    MAX_INPUT_LENGTH,
    build_character_creation_router,
    handle_back,
    handle_callback,
    handle_cancel,
    handle_create,
    handle_step_input,
    handle_summary_input,
)
from app.modules.character.service import (
    BackendUnavailableError,
    CharacterCreationError,
)
from app.modules.character.states import CharacterCreationStates
from app.modules.character.steps import STEPS, position_for_state, prompt_for
from app.utils.constants import (
    CHARACTER_AUTH_REQUIRED_TEXT,
    CHARACTER_CANCELLED_TEXT,
    CHARACTER_EMPTY_INPUT_TEXT,
    CHARACTER_FIRST_STEP_TEXT,
    CHARACTER_IN_PROGRESS_TEXT,
    CHARACTER_NOT_STARTED_TEXT,
    CHARACTER_STALE_TEXT,
    CHARACTER_SUMMARY_HINT_TEXT,
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

    async def set_state(self, state):
        self._state = None if state is None else state.state

    async def get_state(self):
        return self._state

    async def clear(self):
        self.data = {}
        self._state = None


class FakeCreationService:
    def __init__(self):
        self.starts = 0
        self.values = []
        self.generated = []
        self.cancelled = []
        self.data = {}
        self.draft_id = "draft-1"
        self.fail_with = None

    def _maybe_fail(self):
        if self.fail_with is not None:
            raise self.fail_with

    async def start(self, auth):
        self._maybe_fail()
        self.starts += 1
        self.auth = auth
        return {"id": self.draft_id, "data": dict(self.data)}

    async def set_value(self, auth, draft_id, parameter, value):
        self._maybe_fail()
        self.values.append((draft_id, parameter, value))
        self.data[parameter] = value
        return {"id": draft_id, "data": dict(self.data)}

    async def generate_value(self, auth, draft_id, parameter):
        self._maybe_fail()
        self.generated.append((draft_id, parameter))
        value = f"generated-{parameter}"
        self.data[parameter] = value
        return {"id": draft_id, "data": dict(self.data)}

    async def cancel(self, auth, draft_id):
        self._maybe_fail()
        self.cancelled.append(draft_id)


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


def _state_with_auth():
    return FakeState(data={"auth": dict(AUTH)})


def _last_answer(mock):
    return mock.answer.call_args.args[0]


def _started_state(service, state=None):
    state = state or _state_with_auth()
    message = _message()
    asyncio.run(handle_create(message, state, service))
    return state, message


def test_successful_sequential_flow():
    service = FakeCreationService()
    state = _state_with_auth()

    start_message = _message()
    asyncio.run(handle_create(start_message, state, service))
    assert state.state == CharacterCreationStates.name.state
    assert state.data["draft_id"] == "draft-1"
    assert service.starts == 1
    assert "Step 1/3" in _last_answer(start_message)

    name_message = _message("  Aria  ")
    asyncio.run(handle_step_input(name_message, state, service))
    assert service.values == [("draft-1", "name", "Aria")]
    assert state.state == CharacterCreationStates.race.state
    assert "Step 2/3" in _last_answer(name_message)

    race_callback = _callback("cc:set:race:Elf")
    asyncio.run(handle_callback(race_callback, state, service))
    assert service.values[-1] == ("draft-1", "kind", "Elf")
    assert state.state == CharacterCreationStates.spec_class.state
    assert "Step 3/3" in _last_answer(race_callback.message)

    class_callback = _callback("cc:gen:spec_class")
    asyncio.run(handle_callback(class_callback, state, service))
    assert service.generated == [("draft-1", "spec_class")]
    assert state.state == CharacterCreationStates.summary.state
    summary_text = _last_answer(class_callback.message)
    assert "Name: Aria" in summary_text
    assert "Race: Elf" in summary_text
    assert "Class: generated-spec_class" in summary_text
    assert service.data == {
        "name": "Aria",
        "kind": "Elf",
        "spec_class": "generated-spec_class",
    }


def test_manual_input_for_name_race_and_class():
    service = FakeCreationService()
    state, _ = _started_state(service)

    for text, expected_field, expected_state in [
        ("Bjorn", "name", CharacterCreationStates.race),
        ("Dwarf", "kind", CharacterCreationStates.spec_class),
        ("Rogue", "spec_class", CharacterCreationStates.summary),
    ]:
        message = _message(text)
        asyncio.run(handle_step_input(message, state, service))
        assert service.values[-1][1] == expected_field
        assert service.values[-1][2] == text
        assert state.state == expected_state.state


def test_generated_input_for_each_step():
    service = FakeCreationService()
    state, _ = _started_state(service)

    for callback_data, expected_field, expected_state in [
        ("cc:gen:name", "name", CharacterCreationStates.race),
        ("cc:gen:race", "kind", CharacterCreationStates.spec_class),
        ("cc:gen:spec_class", "spec_class", CharacterCreationStates.summary),
    ]:
        callback = _callback(callback_data)
        asyncio.run(handle_callback(callback, state, service))
        assert service.generated[-1][1] == expected_field
        assert state.state == expected_state.state


def test_invalid_input_empty_is_rejected_locally():
    service = FakeCreationService()
    state, _ = _started_state(service)

    message = _message("   ")
    asyncio.run(handle_step_input(message, state, service))

    assert service.values == []
    assert state.state == CharacterCreationStates.name.state
    assert _last_answer(message) == CHARACTER_EMPTY_INPUT_TEXT


def test_invalid_input_too_long_is_rejected_locally():
    service = FakeCreationService()
    state, _ = _started_state(service)

    message = _message("x" * (MAX_INPUT_LENGTH + 1))
    asyncio.run(handle_step_input(message, state, service))

    assert service.values == []
    assert state.state == CharacterCreationStates.name.state
    assert _last_answer(message) == CHARACTER_TOO_LONG_TEXT


def test_invalid_input_backend_rejection_keeps_step():
    service = FakeCreationService()
    state, _ = _started_state(service)
    service.fail_with = CharacterCreationError(
        "Name must be no more than 100 characters."
    )

    message = _message("x" * 150)
    asyncio.run(handle_step_input(message, state, service))

    assert service.values == []
    assert state.state == CharacterCreationStates.name.state
    assert "no more than 100 characters" in _last_answer(message)


def test_cancel_discards_draft_and_clears_state():
    service = FakeCreationService()
    state, _ = _started_state(service)

    message = _message("/cancel")
    asyncio.run(handle_cancel(message, state, service))

    assert service.cancelled == ["draft-1"]
    assert state.state is None
    assert state.data == {}
    assert _last_answer(message) == CHARACTER_CANCELLED_TEXT


def test_cancel_without_draft_replies_not_started():
    service = FakeCreationService()
    state = FakeState(data={"auth": dict(AUTH)})

    message = _message("/cancel")
    asyncio.run(handle_cancel(message, state, service))

    assert service.cancelled == []
    assert _last_answer(message) == CHARACTER_NOT_STARTED_TEXT


def test_cancel_keeps_state_when_backend_unavailable():
    service = FakeCreationService()
    state, _ = _started_state(service)
    service.fail_with = BackendUnavailableError("broker down")

    message = _message("/cancel")
    asyncio.run(handle_cancel(message, state, service))

    assert state.data["draft_id"] == "draft-1"
    assert _last_answer(message) == CHARACTER_UNAVAILABLE_TEXT


def test_back_returns_to_previous_step_without_backend_call():
    service = FakeCreationService()
    state, _ = _started_state(service)
    asyncio.run(handle_step_input(_message("Aria"), state, service))
    assert state.state == CharacterCreationStates.race.state

    message = _message("/back")
    asyncio.run(handle_back(message, state))

    assert state.state == CharacterCreationStates.name.state
    assert "Step 1/3" in _last_answer(message)
    assert service.values == [("draft-1", "name", "Aria")]
    assert service.starts == 1


def test_back_on_first_step_replies_first_step():
    service = FakeCreationService()
    state, _ = _started_state(service)

    message = _message("/back")
    asyncio.run(handle_back(message, state))

    assert state.state == CharacterCreationStates.name.state
    assert _last_answer(message) == CHARACTER_FIRST_STEP_TEXT


def test_back_from_summary_returns_to_class_step():
    service = FakeCreationService()
    state, _ = _started_state(service)
    asyncio.run(handle_step_input(_message("Aria"), state, service))
    asyncio.run(handle_callback(_callback("cc:set:race:Elf"), state, service))
    asyncio.run(handle_callback(_callback("cc:gen:spec_class"), state, service))
    assert state.state == CharacterCreationStates.summary.state

    message = _message("/back")
    asyncio.run(handle_back(message, state))

    assert state.state == CharacterCreationStates.spec_class.state


def test_back_without_draft_replies_not_started():
    state = FakeState(data={"auth": dict(AUTH)})
    message = _message("/back")
    asyncio.run(handle_back(message, state))
    assert _last_answer(message) == CHARACTER_NOT_STARTED_TEXT


def test_create_requires_authentication():
    service = FakeCreationService()
    state = FakeState()

    message = _message("/create_character")
    asyncio.run(handle_create(message, state, service))

    assert service.starts == 0
    assert state.state is None
    assert _last_answer(message) == CHARACTER_AUTH_REQUIRED_TEXT


def test_repeated_create_command_does_not_create_second_draft():
    service = FakeCreationService()
    state, _ = _started_state(service)

    message = _message("/create_character")
    asyncio.run(handle_create(message, state, service))

    assert service.starts == 1
    assert state.state == CharacterCreationStates.name.state
    assert _last_answer(message) == CHARACTER_IN_PROGRESS_TEXT


def test_repeated_stale_preset_button_is_ignored():
    service = FakeCreationService()
    state, _ = _started_state(service)

    stale = _callback("cc:set:race:Elf")
    asyncio.run(handle_callback(stale, state, service))

    assert service.values == []
    assert state.state == CharacterCreationStates.name.state
    stale.answer.assert_awaited_once_with(
        CHARACTER_STALE_TEXT, show_alert=True
    )


def test_stale_button_after_step_is_ignored():
    service = FakeCreationService()
    state, _ = _started_state(service)
    asyncio.run(handle_step_input(_message("Aria"), state, service))

    stale = _callback("cc:set:name:Elf")
    asyncio.run(handle_callback(stale, state, service))

    assert len(service.values) == 1
    assert state.state == CharacterCreationStates.race.state


def test_text_outside_wizard_replies_not_started():
    service = FakeCreationService()
    state = FakeState(data={"auth": dict(AUTH)})

    message = _message("Hello")
    asyncio.run(handle_step_input(message, state, service))

    assert service.values == []
    assert _last_answer(message) == CHARACTER_NOT_STARTED_TEXT


def test_summary_state_replies_with_hint():
    state = FakeState(
        data={"auth": dict(AUTH), "draft_id": "draft-1"},
        state=CharacterCreationStates.summary.state,
    )
    message = _message("something")
    asyncio.run(handle_summary_input(message, state))
    assert _last_answer(message) == CHARACTER_SUMMARY_HINT_TEXT


def test_backend_failure_on_start_leaves_state_empty():
    service = FakeCreationService()
    service.fail_with = BackendUnavailableError("broker down")
    state = _state_with_auth()

    message = _message("/create_character")
    asyncio.run(handle_create(message, state, service))

    assert state.state is None
    assert "draft_id" not in state.data
    assert _last_answer(message) == CHARACTER_UNAVAILABLE_TEXT


def test_backend_failure_on_value_keeps_current_step():
    service = FakeCreationService()
    state, _ = _started_state(service)
    service.fail_with = BackendUnavailableError("broker down")

    message = _message("Aria")
    asyncio.run(handle_step_input(message, state, service))

    assert state.state == CharacterCreationStates.name.state
    assert "draft_id" in state.data
    assert _last_answer(message) == CHARACTER_UNAVAILABLE_TEXT


def test_backend_failure_on_generate_keeps_current_step():
    service = FakeCreationService()
    state, _ = _started_state(service)
    service.fail_with = BackendUnavailableError("broker down")

    callback = _callback("cc:gen:name")
    asyncio.run(handle_callback(callback, state, service))

    assert state.state == CharacterCreationStates.name.state
    assert _last_answer(callback.message) == CHARACTER_UNAVAILABLE_TEXT


def test_cancel_callback_discards_draft():
    service = FakeCreationService()
    state, _ = _started_state(service)

    callback = _callback(CALLBACK_CANCEL)
    asyncio.run(handle_callback(callback, state, service))

    assert service.cancelled == ["draft-1"]
    assert state.state is None
    assert _last_answer(callback.message) == CHARACTER_CANCELLED_TEXT


def test_back_callback_returns_to_previous_step():
    service = FakeCreationService()
    state, _ = _started_state(service)
    asyncio.run(handle_step_input(_message("Aria"), state, service))

    callback = _callback(CALLBACK_BACK)
    asyncio.run(handle_callback(callback, state, service))

    assert state.state == CharacterCreationStates.name.state
    assert "Step 1/3" in _last_answer(callback.message)


def test_manual_button_hint():
    service = FakeCreationService()
    state, _ = _started_state(service)

    callback = _callback("cc:manual:race")
    asyncio.run(handle_callback(callback, state, service))

    callback.answer.assert_awaited_once()
    assert service.values == []


def test_step_order_follows_domain_required_fields():
    assert [step.field for step in STEPS] == ["name", "kind", "spec_class"]
    assert [step.position for step in STEPS] == ["name", "race", "spec_class"]
    assert STEPS[1].field == "kind"
    assert STEPS[2].field == "spec_class"


def test_prompts_mention_navigation_commands():
    for step in STEPS:
        prompt = prompt_for(step)
        assert "/back" in prompt
        assert "/cancel" in prompt


def test_step_keyboard_contains_options_and_generate():
    race_step = STEPS[1]
    keyboard = step_keyboard(race_step)
    rows = keyboard.inline_keyboard
    callback_data = [button.callback_data for row in rows for button in row]
    assert "cc:set:race:Human" in callback_data
    assert "cc:gen:race" in callback_data
    assert "cc:manual:race" in callback_data
    assert CALLBACK_BACK in callback_data
    assert CALLBACK_CANCEL in callback_data


def test_name_step_keyboard_has_no_preset_options():
    keyboard = step_keyboard(STEPS[0])
    callback_data = [
        button.callback_data for row in keyboard.inline_keyboard for button in row
    ]
    assert not any(data.startswith("cc:set:") for data in callback_data)
    assert "cc:gen:name" in callback_data


def test_router_registers_expected_handlers():
    router = build_character_creation_router()
    assert router.name == "character_creation"
    assert len(router.message.handlers) == 5
    assert len(router.callback_query.handlers) == 1


def test_position_for_state_matches_states_group():
    assert position_for_state(CharacterCreationStates.race.state) == "race"
    assert position_for_state("nope") is None
    assert position_for_state(None) is None
