import asyncio
from types import SimpleNamespace
from unittest.mock import AsyncMock

from app.modules.character.management import (
    CharacterManagementService,
    handle_management_callback,
)
from app.modules.character.sheet import sheet_keyboard, sheet_page_count, sheet_text

CHARACTER = {
    "id": "char-1",
    "name": "Aria",
    "kind": "Elf",
    "spec_class": "Wizard",
    "level": 3,
    "background": "Sage",
    "alignment": "Neutral Good",
    "experience_points": 900,
    "stats": {"strength": 8, "dexterity": 16, "constitution": 12, "intelligence": 18, "wisdom": 10, "charisma": 13},
    "modifiers": {"strength": -1, "dexterity": 3, "constitution": 1, "intelligence": 4, "wisdom": 0, "charisma": 1},
    "combat": {"current_hp": 18, "max_hp": 20, "temp_hp": 2, "armor_class": 13, "initiative": 3, "speed": 30, "hit_dice_total": "3d6", "hit_dice_remaining": 2, "proficiency_bonus": 2},
    "saving_throws": {"intelligence": True},
    "skills": [{"name": "Arcana", "ability": "intelligence", "proficiency": True}],
    "features": [{"name": "Arcane Recovery", "description": "Recover spell slots."}],
    "proficiencies": [{"category": "armor", "name": "Light armor"}],
    "backstory": {"backstory": "A long road."},
    "personality": {"personality_traits": "Curious", "ideals": "Knowledge", "bonds": "Home", "flaws": "Proud"},
}


class State:
    def __init__(self, data):
        self.data = data

    async def get_data(self):
        return dict(self.data)

    async def update_data(self, **values):
        self.data.update(values)


def callback(data):
    item = AsyncMock()
    item.data = data
    item.message = AsyncMock()
    return item


def test_sections_render_available_values_and_missing_optional_values():
    assert "INT: 18 (+4)" in sheet_text(CHARACTER, "abilities")
    assert "Current HP: 18" in sheet_text(CHARACTER, "combat")
    assert "Arcana (intelligence): proficient" in sheet_text(CHARACTER, "skills")
    assert "Armor: Light armor" in sheet_text(CHARACTER, "features")
    assert "No backstory has been saved" not in sheet_text(CHARACTER, "backstory")
    assert "Subclass: Not available" in sheet_text(CHARACTER, "overview")


def test_non_spellcasting_and_inventory_sections_are_explicit():
    assert "not available" in sheet_text(CHARACTER, "spells")
    assert "not available" in sheet_text(CHARACTER, "inventory")


def test_section_switch_edits_existing_message_and_keeps_navigation():
    state = State({"selected_character": CHARACTER})
    item = callback("cs:char-1:combat:0")
    asyncio.run(handle_management_callback(item, state, None, None))
    item.message.edit_text.assert_awaited_once()
    assert "Current HP: 18" in item.message.edit_text.await_args.args[0]
    assert item.message.edit_text.await_args.kwargs["reply_markup"].inline_keyboard[-1][0].text == "⬅️ Back to Characters"


def test_large_section_paginates_without_dropping_lines():
    character = dict(CHARACTER, features=[{"name": f"Feature {index}", "description": "Details"} for index in range(40)])
    pages = sheet_page_count(character, "features")
    assert pages > 1
    for page in range(pages):
        assert sheet_text(character, "features", page)
    markup = sheet_keyboard("char-1", "features", 1, pages)
    assert any(button.text == "⬅️ Previous" for row in markup.inline_keyboard for button in row)


def test_character_get_sends_authenticated_detail_request():
    rabbit = SimpleNamespace(request=AsyncMock(return_value=SimpleNamespace(payload={"ok": True, "character": CHARACTER})))
    service = CharacterManagementService(rabbit)
    result = asyncio.run(service.get({"user_id": "user-1", "provider": "telegram", "provider_user_id": "7"}, "char-1"))
    assert result["id"] == "char-1"
    assert rabbit.request.await_args.args[0].value == "character.get.command"
    assert rabbit.request.await_args.kwargs["user_id"] == "user-1"
