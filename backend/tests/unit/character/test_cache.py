import asyncio
import fnmatch
import importlib

from src.modules.character.models import Character, Skill
from src.modules.character.skills.schemas import SkillAbility, SkillCreateSchema
from src.modules.character.skills.service import SkillService
from tests.utils import FakeRepo, FakeUnitOfWork, build_guard, build_owned_character


class _Patch:
    def setattr(self, target, value):
        module, _, attr = target.rpartition(".")
        setattr(importlib.import_module(module), attr, value)


class FakeCache:
    def __init__(self):
        self.store = {}

    async def get(self, key):
        return self.store.get(key)

    async def set(self, key, value, ttl=None):
        self.store[key] = value

    async def delete_pattern(self, pattern):
        for key in fnmatch.filter(self.store, pattern):
            self.store.pop(key, None)


class CountingRepo(FakeRepo):
    def __init__(self, model):
        super().__init__(model)
        self.reads = 0

    async def get_many(self, skip=0, limit=None, **kwargs):
        self.reads += 1
        return await super().get_many(skip=skip, limit=limit, **kwargs)


class DummyUser:
    def __init__(self, id):
        self.id = id


def test_skills_get_is_cached_and_write_invalidates(monkeypatch=_Patch()):
    fake = FakeCache()
    monkeypatch.setattr("src.modules.character.skills.service.cache", fake)

    async def flow():
        user_repo = FakeRepo(model=DummyUser)
        character_repo = FakeRepo(model=Character)
        guard = build_guard(character_repo, user_repo, "user-1")
        repo = CountingRepo(model=Skill)
        svc = SkillService(ownership_guard=guard, skill_repository=repo, unit_of_work=FakeUnitOfWork())
        character = build_owned_character(character_repo)
        char_id = character.id

        await svc.add_skill(
            "user-1", char_id, SkillCreateSchema(name="Athletics", ability=SkillAbility.strength)
        )

        first = await svc.get_skills("user-1", char_id)
        assert repo.reads == 1  # first GET reads the DB and fills the cache

        second = await svc.get_skills("user-1", char_id)
        assert repo.reads == 1  # served from cache, no new DB read
        assert {s.name for s in first} == {s.name for s in second} == {"Athletics"}

        await svc.add_skill(
            "user-1", char_id, SkillCreateSchema(name="Perception", ability=SkillAbility.wisdom)
        )
        third = await svc.get_skills("user-1", char_id)
        assert repo.reads == 2  # cache invalidated on write, refetched

    asyncio.run(flow())


if __name__ == "__main__":
    test_skills_get_is_cached_and_write_invalidates()
    print("cache tests passed")