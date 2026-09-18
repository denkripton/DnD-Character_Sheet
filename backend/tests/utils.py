import fnmatch
import uuid

from src.modules.character.models import Character
from src.modules.character.utils.ownership import CharacterOwnershipGuard


class FakeRedis:
    def __init__(self, fail: bool = False):
        self.store = {}
        self.expirations = {}
        self.fail = fail
        self.closed = False

    def _check(self):
        if self.fail:
            raise ConnectionError("redis is unavailable")

    async def get(self, key):
        self._check()
        return self.store.get(key)

    async def set(self, key, value, ex=None, **kwargs):
        self._check()
        self.store[key] = value
        if ex is not None:
            self.expirations[key] = ex
        return True

    async def delete(self, key):
        self._check()
        self.store.pop(key, None)
        self.expirations.pop(key, None)
        return 1

    async def exists(self, key):
        self._check()
        return 1 if key in self.store else 0

    async def incr(self, key):
        self._check()
        value = int(self.store.get(key, 0)) + 1
        self.store[key] = value
        return value

    async def expire(self, key, seconds):
        self._check()
        self.expirations[key] = seconds
        return True

    async def ttl(self, key):
        self._check()
        return self.expirations.get(key, -1)

    async def scan_iter(self, match=None, **kwargs):
        self._check()
        for key in list(self.store):
            if match is None or fnmatch.fnmatch(key, match):
                yield key

    async def ping(self):
        self._check()
        return True

    async def aclose(self):
        self.closed = True


class FakeSession:
    async def commit(self):
        pass

    async def refresh(self, obj):
        return obj

    async def rollback(self):
        pass


class FakeUnitOfWork:
    def __init__(self):
        self.commit_calls = 0
        self.rollback_calls = 0

    async def commit(self):
        self.commit_calls += 1

    async def rollback(self):
        self.rollback_calls += 1

    async def refresh(self, obj):
        return obj


class FakeRepo:
    def __init__(self, model):
        self.model = model
        self.session = FakeSession()
        self.rows = []

    async def get_by_id(self, id):
        return next((r for r in self.rows if getattr(r, "id", None) == id), None)

    async def get_by_email(self, email):
        return next((r for r in self.rows if getattr(r, "email", None) == email), None)

    async def get_one(self, **kwargs):
        for row in self.rows:
            if all(
                value is None or getattr(row, key, None) == value
                for key, value in kwargs.items()
            ):
                return row
        return None

    async def get_many(self, skip: int = 0, limit: int = None, **kwargs):
        rows = [
            row
            for row in self.rows
            if all(
                value is None or getattr(row, key, None) == value
                for key, value in kwargs.items()
            )
        ]
        if limit is None:
            return rows[skip:]
        return rows[skip : skip + limit]

    async def create(self, **kwargs):
        if kwargs.get("id") is None:
            kwargs["id"] = uuid.uuid4()
        obj = self.model(**kwargs)
        self.rows.append(obj)
        return obj

    async def delete_obj(self, id):
        row = next(r for r in self.rows if getattr(r, "id", None) == id)
        self.rows.remove(row)
        return row


def build_guard(character_repo, user_repo, user_id):
    user = type("User", (), {"id": user_id})()
    user_repo.rows.append(user)
    return CharacterOwnershipGuard(
        character_repository=character_repo,
        user_repository=user_repo,
    )


def build_owned_character(
    character_repo,
    character_id=None,
    owner_id="user-1",
    spec_class="Barbarian",
    kind="Human",
):
    character = Character(
        id=character_id or uuid.uuid4(),
        name="Grog",
        spec_class=spec_class,
        kind=kind,
        level=1,
        experience_points=0,
        owner_id=owner_id,
    )
    character_repo.rows.append(character)
    return character