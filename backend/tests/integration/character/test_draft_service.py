import asyncio
from unittest.mock import patch

import pytest
from src.modules.character.draft.service import CharacterDraftService
from src.modules.character.models import CharacterDraft
from src.modules.character.utils.random_character import KINDS, NAMES, SPEC_CLASSES
from src.utils.exceptions import ServiceError
from tests.utils import FakeRepo, FakeUnitOfWork


class DummyUser:
    def __init__(self, id):
        self.id = id


def _service():
    user_repo = FakeRepo(model=DummyUser)
    user_repo.rows.append(DummyUser("user-1"))
    user_repo.rows.append(DummyUser("user-2"))
    draft_repo = FakeRepo(model=CharacterDraft)
    uow = FakeUnitOfWork()
    service = CharacterDraftService(
        draft_repository=draft_repo,
        user_repository=user_repo,
        unit_of_work=uow,
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
