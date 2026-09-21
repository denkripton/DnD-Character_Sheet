import asyncio

import pytest

from src.utils.exceptions import ServiceError
from src.modules.character.utils.ownership import CharacterOwnershipGuard
from tests.utils import FakeRepo


class DummyUser:
    def __init__(self, id):
        self.id = id


class DummyCharacter:
    def __init__(self, id, owner_id):
        self.id = id
        self.owner_id = owner_id


def _guard(user_rows=None, character_rows=None):
    user_repo = FakeRepo(model=DummyUser)
    for row in user_rows or []:
        user_repo.rows.append(row)
    character_repo = FakeRepo(model=DummyCharacter)
    for row in character_rows or []:
        character_repo.rows.append(row)
    return CharacterOwnershipGuard(
        character_repository=character_repo,
        user_repository=user_repo,
    )


def test_get_owned_returns_character():
    guard = _guard(
        user_rows=[DummyUser(id="user-1")],
        character_rows=[DummyCharacter(id="char-1", owner_id="user-1")],
    )

    async def flow():
        character = await guard.get_owned("user-1", "char-1")
        assert character.id == "char-1"

    asyncio.run(flow())


def test_missing_user_raises():
    guard = _guard(
        character_rows=[DummyCharacter(id="char-1", owner_id="user-1")]
    )

    async def flow():
        with pytest.raises(ServiceError) as exc_info:
            await guard.get_owned("missing-user", "char-1")
        assert exc_info.value.status_code == 422

    asyncio.run(flow())


def test_unowned_character_raises():
    guard = _guard(
        user_rows=[DummyUser(id="user-1")],
        character_rows=[DummyCharacter(id="char-1", owner_id="user-2")],
    )

    async def flow():
        with pytest.raises(ServiceError) as exc_info:
            await guard.get_owned("user-1", "char-1")
        assert exc_info.value.status_code == 422

    asyncio.run(flow())


if __name__ == "__main__":
    for name, fn in sorted(globals().items()):
        if name.startswith("test_") and callable(fn):
            fn()
    print("ownership tests passed")