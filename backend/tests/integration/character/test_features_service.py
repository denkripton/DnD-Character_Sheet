import asyncio
import uuid

CHAR_ID = uuid.uuid4()

import pytest
from pydantic import ValidationError

from src.exceptions import ServiceError
from src.modules.character.features.schemas import FeatureCreateSchema
from src.modules.character.features.service import FeatureService
from src.modules.character.models import Character, Feature
from tests.utils import FakeRepo, build_guard, build_owned_character


class DummyUser:
    def __init__(self, id):
        self.id = id


def _build():
    user_repo = FakeRepo(model=DummyUser)
    character_repo = FakeRepo(model=Character)
    repo = FakeRepo(model=Feature)
    guard = build_guard(character_repo, user_repo, "user-1")
    build_owned_character(character_repo, CHAR_ID)
    service = FeatureService(ownership_guard=guard, feature_repository=repo)
    return service, repo, "user-1"


def test_add_feature_creates():
    service, _, user_id = _build()

    async def flow():
        created = await service.add_feature(
            user_id, CHAR_ID, FeatureCreateSchema(name="Rage", description="Enter a rage")
        )
        assert created.name == "Rage"
        assert created.description == "Enter a rage"

    asyncio.run(flow())


def test_update_feature_changes_fields():
    service, _, user_id = _build()

    async def flow():
        created = await service.add_feature(
            user_id, CHAR_ID, FeatureCreateSchema(name="Rage", description="Enter a rage")
        )
        updated = await service.update_feature(
            user_id, CHAR_ID, created.id, FeatureCreateSchema(name="Reckless Attack")
        )
        assert updated.name == "Reckless Attack"
        assert updated.description == ""

    asyncio.run(flow())


def test_update_feature_missing_raises():
    service, _, user_id = _build()

    async def flow():
        with pytest.raises(ServiceError) as exc_info:
            await service.update_feature(user_id, CHAR_ID, "missing", FeatureCreateSchema(name="X"))
        assert exc_info.value.status_code == 422

    asyncio.run(flow())


def test_delete_feature_removes():
    service, repo, user_id = _build()

    async def flow():
        created = await service.add_feature(
            user_id, CHAR_ID, FeatureCreateSchema(name="Rage")
        )
        result = await service.delete_feature(user_id, CHAR_ID, created.id)
        assert result == {"message": "Feature has been deleted"}
        assert repo.rows == []

    asyncio.run(flow())


def test_create_schema_rejects_empty_name():
    with pytest.raises(ValidationError):
        FeatureCreateSchema(name="")


if __name__ == "__main__":
    for name, fn in sorted(globals().items()):
        if name.startswith("test_") and callable(fn):
            fn()
    print("features service tests passed")