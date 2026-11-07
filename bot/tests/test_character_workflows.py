import asyncio
from types import SimpleNamespace
from unittest.mock import AsyncMock

import pytest
from app.modules.backstory.keyboards import (
    CALLBACK_ACCEPT,
    CALLBACK_GENERATE,
    CALLBACK_REGENERATE,
)
from app.modules.backstory.router import handle_backstory_callback
from app.modules.backstory.states import BackstoryStates
from app.modules.character.keyboards import (
    CALLBACK_CONFIRM,
    CALLBACK_FULL_METHOD,
    CALLBACK_GEN_FULL,
    CALLBACK_GEN_STEP,
    CALLBACK_SAVE,
    CALLBACK_SET,
)
from app.modules.character.router import (
    handle_callback,
    handle_cancel,
    handle_create,
    handle_edit_character,
    handle_step_input,
)
from app.modules.character.service import BackendUnavailableError
from app.modules.character.states import CharacterCreationStates

AUTH = {
    "provider": "telegram",
    "provider_user_id": "7",
    "user_id": "user-1",
    "username": "hero",
    "access_token": "token",
}


class WorkflowState:
    def __init__(self, data=None, state=None):
        self.data = dict(data or {})
        self._state = state

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


class WorkflowService:
    def __init__(self):
        self.draft_data = {}
        self.saved = []
        self.cancelled = []
        self.generated_backstories = []
        self.backstory_version = 0
        self.persisted = {
            "char-1": {
                "id": "char-1",
                "name": "Aria",
                "kind": "Elf",
                "spec_class": "Wizard",
                "backstory": "Original story.",
            }
        }
        self.fail_backstory = None

    async def start(self, auth):
        self.draft_data = {}
        return {"id": "draft-1", "data": {}}

    async def set_value(self, auth, draft_id, parameter, value):
        self.draft_data[parameter] = value
        return {"id": draft_id, "data": dict(self.draft_data)}

    async def generate_value(self, auth, draft_id, parameter):
        value = f"generated-{parameter}"
        self.draft_data[parameter] = value
        return {"id": draft_id, "data": dict(self.draft_data)}

    async def generate_stats(self, auth, draft_id, method):
        return {
            "stats": {
                "strength": 15,
                "dexterity": 14,
                "constitution": 13,
                "intelligence": 12,
                "wisdom": 10,
                "charisma": 8,
            },
            "modifiers": {
                "strength": 2,
                "dexterity": 2,
                "constitution": 1,
                "intelligence": 1,
                "wisdom": 0,
                "charisma": -1,
            },
        }

    async def generate_character(self, auth, draft_id, method):
        self.draft_data = {
            "name": "Lyra",
            "kind": "Elf",
            "spec_class": "Wizard",
            "alignment": "True Neutral",
            "background": "Sage",
        }
        return {
            "draft": {"id": draft_id, "data": dict(self.draft_data)},
            "stats": {"strength": 15},
            "modifiers": {"strength": 2},
        }

    async def save_character(self, auth, draft_id, backstory=None):
        target_id = self.draft_data.get("target_character_id", "char-1")
        character = dict(self.persisted.get(target_id, {"id": target_id}))
        character.update(self.draft_data)
        if backstory is not None:
            character["backstory"] = backstory
        self.persisted[target_id] = character
        self.saved.append((draft_id, backstory))
        return {"character_id": target_id, "character": character}

    async def start_edit(self, auth, character_id):
        character = dict(self.persisted[character_id])
        self.draft_data = dict(character)
        self.draft_data["target_character_id"] = character_id
        return {
            "id": "edit-draft-1",
            "target_character_id": character_id,
            "data": character,
        }

    async def cancel(self, auth, draft_id):
        self.cancelled.append(draft_id)

    async def generate_backstory(
        self,
        auth,
        character_id,
        prompt=None,
        model=None,
        provider=None,
        draft_id=None,
    ):
        if self.fail_backstory is not None:
            raise self.fail_backstory
        identifier = draft_id or character_id
        self.generated_backstories.append((identifier, dict(self.draft_data), prompt))
        self.backstory_version += 1
        return f"Generated story {self.backstory_version}."

    async def save_backstory(self, auth, character_id, backstory):
        self.persisted[character_id]["backstory"] = backstory


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


def _state():
    return WorkflowState(data={"auth": dict(AUTH)})


def _full_summary(service, state):
    asyncio.run(handle_create(_message("/create"), state, service))
    asyncio.run(handle_callback(_callback(CALLBACK_GEN_FULL), state, service))
    asyncio.run(
        handle_callback(_callback(f"{CALLBACK_FULL_METHOD}:standard"), state, service)
    )
    assert state._state == CharacterCreationStates.generation_result.state


def _step_summary(service, state):
    asyncio.run(handle_create(_message("/create"), state, service))
    asyncio.run(handle_callback(_callback(CALLBACK_GEN_STEP), state, service))
    asyncio.run(handle_step_input(_message("Aria"), state, service))
    asyncio.run(handle_callback(_callback(f"{CALLBACK_SET}:race:Elf"), state, service))
    asyncio.run(
        handle_step_input(_message("Wizard"), state, service)
    )
    asyncio.run(handle_callback(_callback("cc:method:random"), state, service))
    asyncio.run(handle_callback(_callback(CALLBACK_CONFIRM), state, service))
    assert state._state == CharacterCreationStates.summary.state


def _start_backstory(service, state):
    asyncio.run(handle_callback(_callback("cc:backstory"), state, service))
    assert state._state == BackstoryStates.prompt.state


def test_full_generation_save_clears_draft_and_does_not_duplicate_on_repeat():
    service = WorkflowService()
    state = _state()
    _full_summary(service, state)

    asyncio.run(handle_callback(_callback(CALLBACK_SAVE), state, service))
    asyncio.run(handle_callback(_callback(CALLBACK_SAVE), state, service))

    assert service.saved == [("draft-1", None)]
    assert state._state == BackstoryStates.character_saved.state
    assert "draft_id" not in state.data


@pytest.mark.parametrize("summary_builder", [_full_summary, _step_summary])
def test_creation_can_generate_backstory_and_save_character_atomically(summary_builder):
    service = WorkflowService()
    state = _state()
    summary_builder(service, state)
    _start_backstory(service, state)

    asyncio.run(handle_backstory_callback(_callback(CALLBACK_GENERATE), state, service))
    asyncio.run(handle_backstory_callback(_callback(CALLBACK_ACCEPT), state, service))

    assert service.saved == [("draft-1", "Generated story 1.")]
    assert service.persisted["char-1"]["backstory"] == "Generated story 1."
    assert state._state == BackstoryStates.character_saved.state


def test_backstory_regeneration_only_persists_the_accepted_version():
    service = WorkflowService()
    state = _state()
    _full_summary(service, state)
    _start_backstory(service, state)

    asyncio.run(handle_backstory_callback(_callback(CALLBACK_GENERATE), state, service))
    asyncio.run(handle_backstory_callback(_callback(CALLBACK_REGENERATE), state, service))

    assert service.saved == []
    assert service.persisted["char-1"]["backstory"] == "Original story."
    assert state.data["backstory"] == "Generated story 2."

    asyncio.run(handle_backstory_callback(_callback(CALLBACK_ACCEPT), state, service))
    assert service.saved == [("draft-1", "Generated story 2.")]


def test_cancelled_creation_does_not_persist_and_future_creation_starts_cleanly():
    service = WorkflowService()
    state = _state()
    _full_summary(service, state)

    asyncio.run(handle_cancel(_message("/cancel"), state, service))
    assert service.cancelled == ["draft-1"]
    assert service.saved == []
    assert state.data == {}
    assert state._state is None

    state.data["auth"] = dict(AUTH)
    asyncio.run(handle_create(_message("/create"), state, service))
    assert state.data["draft_id"] == "draft-1"
    assert state._state == CharacterCreationStates.generation_mode.state


def test_edit_save_without_backstory_regeneration_preserves_existing_backstory():
    service = WorkflowService()
    state = _state()
    asyncio.run(
        handle_edit_character(_message("/edit_character char-1"), state, service)
    )
    asyncio.run(handle_callback(_callback(CALLBACK_SAVE), state, service))

    assert service.saved == [("edit-draft-1", None)]
    assert service.persisted["char-1"]["backstory"] == "Original story."


def test_edit_can_generate_backstory_and_save_or_cancel_without_mutating_original():
    service = WorkflowService()
    state = _state()
    asyncio.run(
        handle_edit_character(_message("/edit_character char-1"), state, service)
    )
    asyncio.run(handle_callback(_callback("cc:backstory"), state, service))
    asyncio.run(handle_backstory_callback(_callback(CALLBACK_GENERATE), state, service))
    asyncio.run(handle_backstory_callback(_callback(CALLBACK_ACCEPT), state, service))

    assert service.saved == [("edit-draft-1", "Generated story 1.")]
    assert service.persisted["char-1"]["backstory"] == "Generated story 1."

    service = WorkflowService()
    state = _state()
    original = dict(service.persisted["char-1"])
    asyncio.run(
        handle_edit_character(_message("/edit_character char-1"), state, service)
    )
    asyncio.run(handle_cancel(_message("/cancel"), state, service))

    assert service.persisted["char-1"] == original
    assert service.saved == []


def test_backstory_uses_current_draft_and_failure_keeps_draft_state():
    service = WorkflowService()
    state = _state()
    _full_summary(service, state)
    state.data["draft_data"]["name"] = "Updated Lyra"
    service.draft_data["name"] = "Updated Lyra"
    _start_backstory(service, state)

    asyncio.run(handle_backstory_callback(_callback(CALLBACK_GENERATE), state, service))

    assert len(service.generated_backstories) == 1
    identifier, draft, prompt = service.generated_backstories[0]
    assert identifier == "draft-1"
    assert draft["name"] == "Updated Lyra"
    assert prompt is None
    assert state.data["backstory"] == "Generated story 1."

    service.fail_backstory = BackendUnavailableError("AI unavailable")
    asyncio.run(handle_backstory_callback(_callback(CALLBACK_REGENERATE), state, service))

    assert state._state == BackstoryStates.review.state
    assert state.data["draft_id"] == "draft-1"
    assert state.data["draft_data"]["name"] == "Updated Lyra"
    assert state.data["backstory"] == "Generated story 1."


def test_backstory_is_not_automatic_or_available_from_main_menu():
    service = WorkflowService()
    state = _state()
    _full_summary(service, state)

    assert service.generated_backstories == []

    from app.modules.start.keyboards import main_menu_keyboard

    labels = [
        button.text
        for row in main_menu_keyboard().keyboard
        for button in row
    ]
    assert "Generate Backstory" not in labels
