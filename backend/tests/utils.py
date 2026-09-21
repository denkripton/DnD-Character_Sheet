import fnmatch
import uuid

from src.modules.character.models import Character
from src.modules.character.utils.ownership import CharacterOwnershipGuard
from src.utils.interfaces.rate_limiter import RateLimitResult


class StubRateLimiter:
    def __init__(self, allowed: bool = True):
        self.allowed = allowed

    async def is_limited(self, user_id, category, max_requests, time_window):
        if self.allowed:
            return RateLimitResult(
                allowed=True,
                current_usage=0,
                max_allowed=max_requests,
                remaining=max_requests,
                retry_after=0,
            )
        return RateLimitResult(
            allowed=False,
            current_usage=max_requests,
            max_allowed=max_requests,
            remaining=0,
            retry_after=time_window,
        )


class FakeRedis:
    def __init__(self, fail: bool = False):
        self.store = {}
        self.expirations = {}
        self.fail = fail
        self.closed = False

    def _check(self):
        if self.fail:
            raise ConnectionError("redis is unavailable")

    def _is_alive(self, key):
        ttl = self.expirations.get(key)
        if ttl is not None and ttl <= 0:
            self.store.pop(key, None)
            self.expirations.pop(key, None)
            return False
        return True

    def advance(self, seconds):
        for key in list(self.expirations):
            remaining = self.expirations[key] - seconds
            if remaining <= 0:
                self.store.pop(key, None)
                self.expirations.pop(key, None)
            else:
                self.expirations[key] = remaining

    async def get(self, key):
        self._check()
        if not self._is_alive(key):
            return None
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
        return 1 if self._is_alive(key) and key in self.store else 0

    async def incr(self, key):
        self._check()
        self._is_alive(key)
        value = int(self.store.get(key, 0)) + 1
        self.store[key] = value
        return value

    async def expire(self, key, seconds):
        self._check()
        self.expirations[key] = seconds
        return True

    async def ttl(self, key):
        self._check()
        self._is_alive(key)
        if key not in self.store:
            return -2
        return self.expirations.get(key, -1)

    def _zstore(self, key):
        if key not in self.store:
            self.store[key] = {}
        if not isinstance(self.store[key], dict):
            raise TypeError("WRONGTYPE Operation against a key holding the wrong kind of value")
        return self.store[key]

    async def zcard(self, key):
        self._check()
        self._is_alive(key)
        zs = self.store.get(key)
        return len(zs) if isinstance(zs, dict) else 0

    async def zadd(self, key, mapping):
        self._check()
        self._is_alive(key)
        zs = self._zstore(key)
        added = 0
        for member, score in mapping.items():
            if member not in zs:
                added += 1
            zs[member] = float(score)
        return added

    async def zremrangebyscore(self, name, min, max):
        self._check()
        self._is_alive(name)
        zs = self.store.get(name)
        if not isinstance(zs, dict):
            return 0
        removed = [member for member, score in zs.items() if min <= score <= max]
        for member in removed:
            del zs[member]
        return len(removed)

    async def zrange(self, key, start, end, withscores=True):
        self._check()
        self._is_alive(key)
        items = sorted(self.store.get(key, {}).items(), key=lambda item: item[1])
        found = items[start : end + 1]
        if withscores:
            return [(member, float(score)) for member, score in found]
        return [member for member, _ in found]

    def pipeline(self):
        return FakePipeline(self)

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


class FakePipeline:
    def __init__(self, redis):
        self._redis = redis
        self._commands = []

    async def __aenter__(self):
        return self

    async def __aexit__(self, *exc):
        return False

    def zremrangebyscore(self, name, min, max):
        self._commands.append(("zremrangebyscore", name, min, max))
        return self

    def zcard(self, name):
        self._commands.append(("zcard", name))
        return self

    def zadd(self, name, mapping):
        self._commands.append(("zadd", name, mapping))
        return self

    def expire(self, name, seconds):
        self._commands.append(("expire", name, seconds))
        return self

    def zrange(self, name, start, end, withscores=True):
        self._commands.append(("zrange", name, start, end, withscores))
        return self

    async def execute(self):
        results = []
        for command in self._commands:
            op = command[0]
            if op == "zremrangebyscore":
                results.append(
                    await self._redis.zremrangebyscore(command[1], command[2], command[3])
                )
            elif op == "zcard":
                results.append(await self._redis.zcard(command[1]))
            elif op == "zadd":
                results.append(await self._redis.zadd(command[1], command[2]))
            elif op == "expire":
                results.append(await self._redis.expire(command[1], command[2]))
            elif op == "zrange":
                results.append(
                    await self._redis.zrange(
                        command[1], command[2], command[3], withscores=command[4]
                    )
                )
        return results


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