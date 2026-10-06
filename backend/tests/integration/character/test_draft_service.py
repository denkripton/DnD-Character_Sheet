import asyncio
from unittest.mock import patch

import pytest
from src.modules.character.draft.service import CharacterDraftService
from src.modules.character.models import Character, CharacterDraft, Stat
from src.modules.character.utils.random_character import KINDS, NAMES, SPEC_CLASSES
from src.utils.exceptions import RateLimitExceeded, ServiceError
from tests.utils import FakeRepo, FakeUnitOfWork, StubRateLimiter


class DummyUser:
    def __init__(self, id):
        self.id = id


def _service(rate_limiter=None):
    user_repo = FakeRepo(model=DummyUser)
    user_repo.rows.append(DummyUser("user-1"))
    user_repo.rows.append(DummyUser("user-2"))
    draft_repo = FakeRepo(model=CharacterDraft)
    uow = FakeUnitOfWork()
    service = CharacterDraftService(
        draft_repository=draft_repo,
        character_repository=FakeRepo(model=Character),
        stats_repository=FakeRepo(model=Stat),
        user_repository=user_repo,
        unit_of_work=uow,
        rate_limiter=rate_limiter or StubRateLimiter(allowed=True),
    )
    return service, draft_repo, uow


def _fixed_generation():
    return patch(
        "src.modules.character.draft.service.generate_random_character",
        return_value={
            "name": "Lyra",
            "spec_class": "Wizard",
            "kind": "Elf",
            "alignment": "True Neutral",
            "background": "Sage",
        },
    )


def test_create_draft_persists_for_user():
    service, draft_repo, uow = _service()

    async def flow():
        draft = await service.create_draft("user-1")
        assert draft.data == {}
        assert draft.id is not None
        assert len(draft_repo.rows) == 1
        assert draft_repo.rows[0].owner_id == "user-1"
        assert uow.commit_calls == 1

    asyncio.run(flow())


def test_create_draft_unknown_user_raises():
    service, draft_repo, _ = _service()

    async def flow():
        with pytest.raises(ServiceError) as exc_info:
            await service.create_draft("ghost")
        assert exc_info.value.status_code == 422
        assert draft_repo.rows == []

    asyncio.run(flow())


def test_sequential_manual_parameter_flow():
    service, draft_repo, uow = _service()

    async def flow():
        draft = await service.create_draft("user-1")
        draft = await service.update_parameter(
            "user-1", draft.id, "name", "Aria"
        )
        assert draft.data == {"name": "Aria"}

        draft = await service.update_parameter(
            "user-1", draft.id, "kind", "Elf"
        )
        assert draft.data == {"name": "Aria", "kind": "Elf"}

        draft = await service.update_parameter(
            "user-1", draft.id, "spec_class", "Wizard"
        )
        assert draft.data == {
            "name": "Aria",
            "kind": "Elf",
            "spec_class": "Wizard",
        }
        assert draft_repo.rows[0].data == draft.data
        assert uow.commit_calls == 4

    asyncio.run(flow())


def test_update_parameter_overwrites_previous_value():
    service, _, _ = _service()

    async def flow():
        draft = await service.create_draft("user-1")
        await service.update_parameter("user-1", draft.id, "name", "Aria")
        draft = await service.update_parameter(
            "user-1", draft.id, "name", "Bjorn"
        )
        assert draft.data["name"] == "Bjorn"

    asyncio.run(flow())


def test_update_parameter_rejects_too_long_name():
    service, _, _ = _service()

    async def flow():
        draft = await service.create_draft("user-1")
        with pytest.raises(ServiceError) as exc_info:
            await service.update_parameter(
                "user-1", draft.id, "name", "x" * 101
            )
        assert exc_info.value.status_code == 422
        assert str(exc_info.value) == "Name must be no more than 100 characters."
        assert service.draft_repo.rows[0].data == {}

    asyncio.run(flow())


def test_update_parameter_rejects_empty_value():
    service, _, _ = _service()

    async def flow():
        draft = await service.create_draft("user-1")
        with pytest.raises(ServiceError) as exc_info:
            await service.update_parameter("user-1", draft.id, "name", "   ")
        assert str(exc_info.value) == "Name cannot be empty."

    asyncio.run(flow())


def test_update_parameter_rejects_unknown_parameter():
    service, _, _ = _service()

    async def flow():
        draft = await service.create_draft("user-1")
        with pytest.raises(ServiceError) as exc_info:
            await service.update_parameter(
                "user-1", draft.id, "alignment_notes", "whatever"
            )
        assert str(exc_info.value) == "Unsupported parameter: alignment_notes."

    asyncio.run(flow())


def test_update_parameter_rejects_non_text_value():
    service, _, _ = _service()

    async def flow():
        draft = await service.create_draft("user-1")
        with pytest.raises(ServiceError) as exc_info:
            await service.update_parameter("user-1", draft.id, "kind", 42)
        assert str(exc_info.value) == "Race must be a text value."

    asyncio.run(flow())


def test_generate_parameter_uses_existing_generation_logic():
    service, _, _ = _service()

    async def flow():
        draft = await service.create_draft("user-1")
        with _fixed_generation():
            draft = await service.generate_parameter(
                "user-1", draft.id, "kind"
            )
        assert draft.data["kind"] == "Elf"

    asyncio.run(flow())


def test_generate_parameter_returns_domain_value():
    service, _, _ = _service()

    async def flow():
        draft = await service.create_draft("user-1")
        draft = await service.generate_parameter("user-1", draft.id, "spec_class")
        assert draft.data["spec_class"] in SPEC_CLASSES

        draft = await service.generate_parameter("user-1", draft.id, "kind")
        assert draft.data["kind"] in KINDS

        draft = await service.generate_parameter("user-1", draft.id, "name")
        assert draft.data["name"] in NAMES

    asyncio.run(flow())


def test_generate_unsupported_parameter_raises():
    service, _, _ = _service()

    async def flow():
        draft = await service.create_draft("user-1")
        with pytest.raises(ServiceError) as exc_info:
            await service.generate_parameter("user-1", draft.id, "level")
        assert str(exc_info.value) == "Generation is not supported for Level."

    asyncio.run(flow())


def test_update_other_user_draft_raises():
    service, _, _ = _service()

    async def flow():
        draft = await service.create_draft("user-1")
        with pytest.raises(ServiceError) as exc_info:
            await service.update_parameter(
                "user-2", draft.id, "name", "Intruder"
            )
        assert "not found" in str(exc_info.value)
        assert service.draft_repo.rows[0].data == {}

    asyncio.run(flow())


def test_update_missing_draft_raises():
    service, _, _ = _service()

    async def flow():
        await service.create_draft("user-1")
        with pytest.raises(ServiceError):
            await service.update_parameter(
                "user-1", "9b1e8f00-0000-0000-0000-000000000000", "name", "Aria"
            )

    asyncio.run(flow())


def test_update_malformed_draft_id_raises():
    service, _, _ = _service()

    async def flow():
        await service.create_draft("user-1")
        with pytest.raises(ServiceError) as exc_info:
            await service.update_parameter("user-1", "not-a-uuid", "name", "Aria")
        assert "not found" in str(exc_info.value)

    asyncio.run(flow())


def test_delete_draft_removes():
    service, _, uow = _service()

    async def flow():
        draft = await service.create_draft("user-1")
        await service.delete_draft("user-1", draft.id)
        assert service.draft_repo.rows == []
        assert uow.commit_calls == 2

    asyncio.run(flow())


def test_delete_other_user_draft_raises():
    service, _, _ = _service()

    async def flow():
        draft = await service.create_draft("user-1")
        with pytest.raises(ServiceError):
            await service.delete_draft("user-2", draft.id)
        assert len(service.draft_repo.rows) == 1

    asyncio.run(flow())


STANDARD_VALUES = [15, 14, 13, 12, 10, 8]
STANDARD_STATS = {
    "strength": 15,
    "dexterity": 14,
    "constitution": 13,
    "intelligence": 12,
    "wisdom": 10,
    "charisma": 8,
}
STANDARD_MODIFIERS = {
    "strength": 2,
    "dexterity": 2,
    "constitution": 1,
    "intelligence": 1,
    "wisdom": 0,
    "charisma": -1,
}


def _fixed_stats_generation(name, values):
    return patch(
        f"src.modules.character.draft.service.{name}",
        return_value=list(values),
    )


def test_generate_stats_standard_array_persists_and_returns_modifiers():
    service, draft_repo, _ = _service()

    async def flow():
        draft = await service.create_draft("user-1")
        result = await service.generate_stats("user-1", draft.id, "standard")

        assert result["stats"] == STANDARD_STATS
        assert result["modifiers"] == STANDARD_MODIFIERS
        assert draft_repo.rows[0].data["stats"] == STANDARD_STATS

    asyncio.run(flow())


def test_generate_stats_random_uses_domain_generator():
    service, draft_repo, _ = _service()

    async def flow():
        draft = await service.create_draft("user-1")
        with _fixed_stats_generation("generate_random_stats", [16, 15, 14, 13, 12, 9]):
            result = await service.generate_stats("user-1", draft.id, "random")

        assert result["stats"]["strength"] == 16
        assert result["modifiers"]["strength"] == 3
        assert draft_repo.rows[0].data["stats"]["strength"] == 16

    asyncio.run(flow())


def test_generate_stats_point_buy_uses_domain_generator():
    service, draft_repo, _ = _service()

    async def flow():
        draft = await service.create_draft("user-1")
        with _fixed_stats_generation("generate_point_buy_stats", STANDARD_VALUES):
            result = await service.generate_stats("user-1", draft.id, "point_buy")

        assert result["stats"] == STANDARD_STATS
        assert draft_repo.rows[0].data["stats"] == STANDARD_STATS

    asyncio.run(flow())


def test_generate_stats_rejects_unsupported_method():
    service, _, _ = _service()

    async def flow():
        draft = await service.create_draft("user-1")
        with pytest.raises(ServiceError) as exc_info:
            await service.generate_stats("user-1", draft.id, "luck")
        assert exc_info.value.status_code == 422
        assert (
            str(exc_info.value)
            == "Unsupported stats generation method: luck."
        )
        assert service.draft_repo.rows[0].data == {}

    asyncio.run(flow())


def test_generate_stats_other_user_draft_raises():
    service, _, _ = _service()

    async def flow():
        draft = await service.create_draft("user-1")
        with pytest.raises(ServiceError) as exc_info:
            await service.generate_stats("user-2", draft.id, "standard")
        assert "not found" in str(exc_info.value)

    asyncio.run(flow())


def test_set_stats_persists_values_and_returns_modifiers():
    service, draft_repo, _ = _service()

    async def flow():
        draft = await service.create_draft("user-1")
        result = await service.set_stats(
            "user-1", draft.id, ["15", "14", "13", "12", "10", "8"]
        )

        assert result["stats"] == STANDARD_STATS
        assert result["modifiers"] == STANDARD_MODIFIERS
        assert draft_repo.rows[0].data["stats"] == STANDARD_STATS

    asyncio.run(flow())


def test_set_stats_accepts_integer_values():
    service, _, _ = _service()

    async def flow():
        draft = await service.create_draft("user-1")
        result = await service.set_stats(
            "user-1", draft.id, STANDARD_VALUES
        )
        assert result["stats"] == STANDARD_STATS

    asyncio.run(flow())


def test_set_stats_preserves_existing_draft_fields():
    service, draft_repo, _ = _service()

    async def flow():
        draft = await service.create_draft("user-1")
        await service.update_parameter("user-1", draft.id, "name", "Aria")
        await service.set_stats("user-1", draft.id, STANDARD_VALUES)

        assert draft_repo.rows[0].data["name"] == "Aria"
        assert draft_repo.rows[0].data["stats"] == STANDARD_STATS

    asyncio.run(flow())


def test_set_stats_rejects_wrong_count():
    service, _, _ = _service()

    async def flow():
        draft = await service.create_draft("user-1")
        with pytest.raises(ServiceError) as exc_info:
            await service.set_stats("user-1", draft.id, ["15", "14", "13"])
        assert exc_info.value.status_code == 422
        assert (
            str(exc_info.value)
            == "Enter exactly six values in order: STR DEX CON INT WIS CHA."
        )
        assert service.draft_repo.rows[0].data == {}

    asyncio.run(flow())


def test_set_stats_rejects_non_numeric_values():
    service, _, _ = _service()

    async def flow():
        draft = await service.create_draft("user-1")
        with pytest.raises(ServiceError) as exc_info:
            await service.set_stats(
                "user-1", draft.id, ["strong", "14", "13", "12", "10", "8"]
            )
        assert str(exc_info.value) == "Stats must be whole numbers."

    asyncio.run(flow())


def test_set_stats_rejects_values_below_minimum():
    service, _, _ = _service()

    async def flow():
        draft = await service.create_draft("user-1")
        with pytest.raises(ServiceError) as exc_info:
            await service.set_stats(
                "user-1", draft.id, ["7", "14", "13", "12", "10", "8"]
            )
        assert str(exc_info.value) == "Each stat must be between 8 and 15."

    asyncio.run(flow())


def test_set_stats_rejects_values_above_maximum():
    service, _, _ = _service()

    async def flow():
        draft = await service.create_draft("user-1")
        with pytest.raises(ServiceError) as exc_info:
            await service.set_stats(
                "user-1", draft.id, ["16", "14", "13", "12", "10", "8"]
            )
        assert str(exc_info.value) == "Each stat must be between 8 and 15."

    asyncio.run(flow())


def test_set_stats_rejects_overspent_point_buy():
    service, _, _ = _service()

    async def flow():
        draft = await service.create_draft("user-1")
        with pytest.raises(ServiceError) as exc_info:
            await service.set_stats(
                "user-1", draft.id, ["15", "15", "15", "10", "8", "8"]
            )
        assert exc_info.value.status_code == 422
        assert (
            str(exc_info.value)
            == "You must spend exactly 27 points! Spent: 29/27."
        )
        assert service.draft_repo.rows[0].data == {}

    asyncio.run(flow())


def test_set_stats_rejects_underspent_point_buy():
    service, _, _ = _service()

    async def flow():
        draft = await service.create_draft("user-1")
        with pytest.raises(ServiceError) as exc_info:
            await service.set_stats(
                "user-1", draft.id, ["8", "8", "8", "8", "8", "8"]
            )
        assert (
            str(exc_info.value)
            == "You must spend exactly 27 points! Spent: 0/27."
        )

    asyncio.run(flow())


def test_set_stats_other_user_draft_raises():
    service, _, _ = _service()

    async def flow():
        draft = await service.create_draft("user-1")
        with pytest.raises(ServiceError) as exc_info:
            await service.set_stats("user-2", draft.id, STANDARD_VALUES)
        assert "not found" in str(exc_info.value)
        assert service.draft_repo.rows[0].data == {}

    asyncio.run(flow())


def test_set_stats_missing_draft_raises():
    service, _, _ = _service()

    async def flow():
        with pytest.raises(ServiceError) as exc_info:
            await service.set_stats("user-1", "not-a-uuid", STANDARD_VALUES)
        assert "not found" in str(exc_info.value)

    asyncio.run(flow())


def test_stats_then_parameters_keep_both_in_draft():
    service, draft_repo, _ = _service()

    async def flow():
        draft = await service.create_draft("user-1")
        await service.set_stats("user-1", draft.id, STANDARD_VALUES)
        draft = await service.update_parameter(
            "user-1", draft.id, "spec_class", "Wizard"
        )

        assert draft.data["stats"] == STANDARD_STATS
        assert draft.data["spec_class"] == "Wizard"
        assert draft_repo.rows[0].data == draft.data

    asyncio.run(flow())


def test_save_character_creates_character_stats_and_deletes_draft():
    service, draft_repo, uow = _service()

    async def flow():
        draft = await service.create_draft("user-1")
        for parameter, value in [
            ("name", "Aria"),
            ("kind", "Elf"),
            ("spec_class", "Wizard"),
        ]:
            await service.update_parameter("user-1", draft.id, parameter, value)
        await service.generate_stats("user-1", draft.id, "standard")
        commits_before = uow.commit_calls

        result = await service.save_character("user-1", draft.id)

        assert set(result) == {"character_id", "character"}
        assert result["character"]["name"] == "Aria"
        assert result["character"]["kind"] == "Elf"
        assert result["character"]["spec_class"] == "Wizard"
        assert len(service.character_repo.rows) == 1
        assert service.character_repo.rows[0].owner_id == "user-1"
        assert len(service.stats_repo.rows) == 1
        assert service.stats_repo.rows[0].strength == STANDARD_STATS["strength"]
        assert service.stats_repo.rows[0].charisma == STANDARD_STATS["charisma"]
        assert draft_repo.rows == []
        assert uow.commit_calls == commits_before + 1

    asyncio.run(flow())


def test_save_character_requires_required_fields():
    service, draft_repo, _ = _service()

    async def flow():
        draft = await service.create_draft("user-1")

        with pytest.raises(ServiceError) as exc_info:
            await service.save_character("user-1", draft.id)

        assert "required" in exc_info.value.message
        assert service.character_repo.rows == []
        assert len(draft_repo.rows) == 1

    asyncio.run(flow())


def test_save_character_rejects_other_user_draft():
    service, _, _ = _service()

    async def flow():
        draft = await service.create_draft("user-1")
        for parameter, value in [
            ("name", "Aria"),
            ("kind", "Elf"),
            ("spec_class", "Wizard"),
        ]:
            await service.update_parameter("user-1", draft.id, parameter, value)

        with pytest.raises(ServiceError) as exc_info:
            await service.save_character("user-2", draft.id)

        assert "not found" in exc_info.value.message
        assert service.character_repo.rows == []

    asyncio.run(flow())


def test_save_character_invalid_stats_rejected():
    service, draft_repo, _ = _service()

    async def flow():
        draft = await service.create_draft("user-1")
        for parameter, value in [
            ("name", "Aria"),
            ("kind", "Elf"),
            ("spec_class", "Wizard"),
        ]:
            await service.update_parameter("user-1", draft.id, parameter, value)
        draft_repo.rows[0].data["stats"] = {
            "strength": 99,
            "dexterity": 14,
            "constitution": 13,
            "intelligence": 12,
            "wisdom": 10,
            "charisma": 8,
        }

        with pytest.raises(ServiceError) as exc_info:
            await service.save_character("user-1", draft.id)

        assert "3 and 20" in exc_info.value.message
        assert service.character_repo.rows == []
        assert len(draft_repo.rows) == 1

    asyncio.run(flow())


def test_save_character_rate_limited():
    service, _, _ = _service(rate_limiter=StubRateLimiter(allowed=False))

    async def flow():
        draft = await service.create_draft("user-1")
        for parameter, value in [
            ("name", "Aria"),
            ("kind", "Elf"),
            ("spec_class", "Wizard"),
        ]:
            await service.update_parameter("user-1", draft.id, parameter, value)

        with pytest.raises(RateLimitExceeded) as exc_info:
            await service.save_character("user-1", draft.id)

        assert "Daily limit reached" in str(exc_info.value)
        assert service.character_repo.rows == []

    asyncio.run(flow())
