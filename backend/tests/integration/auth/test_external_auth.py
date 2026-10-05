import asyncio
import uuid

import pytest
from sqlalchemy.exc import IntegrityError
from src.modules.auth.external_service import ExternalAuthService
from src.modules.auth.models import ExternalIdentity, User
from src.modules.auth.utils import JWT
from src.utils.exceptions import ServiceError
from tests.utils import FakeRepo, FakeUnitOfWork

PROVIDER = "telegram"


class FakeIdentityRepo(FakeRepo):
    async def get_by_provider(self, provider: str, provider_user_id: str):
        return await self.get_one(provider=provider, provider_user_id=provider_user_id)


class ConstraintUnitOfWork:
    def __init__(self, user_repo, identity_repo):
        self._user_repo = user_repo
        self._identity_repo = identity_repo
        self.commit_calls = 0
        self.rollback_calls = 0

    async def commit(self):
        self.commit_calls += 1
        raise IntegrityError("INSERT INTO users ...", {}, Exception("duplicate"))

    async def rollback(self):
        self.rollback_calls += 1
        self._user_repo.rows.clear()
        self._identity_repo.rows.clear()

    async def refresh(self, obj):
        return obj


def _service(user_repo, identity_repo, uow=None):
    return ExternalAuthService(
        user_repository=user_repo,
        external_identity_repository=identity_repo,
        jwt=JWT(),
        unit_of_work=uow or FakeUnitOfWork(),
    )


def test_auth_creates_user_and_identity_on_first_login():
    user_repo = FakeRepo(model=User)
    identity_repo = FakeIdentityRepo(model=ExternalIdentity)
    service = _service(user_repo, identity_repo)

    async def flow():
        result = await service.authenticate_external(PROVIDER, "7")

        assert "access" in result
        assert "refresh" in result
        assert result["access"] != result["refresh"]
        assert result["user"]["username"] == "telegram_7"
        assert len(user_repo.rows) == 1
        assert len(identity_repo.rows) == 1

        user = user_repo.rows[0]
        identity = identity_repo.rows[0]
        assert user.id == identity.user_id
        assert identity.provider == "telegram"
        assert identity.provider_user_id == "7"

    asyncio.run(flow())


def test_repeated_auth_is_idempotent():
    user_repo = FakeRepo(model=User)
    identity_repo = FakeIdentityRepo(model=ExternalIdentity)
    service = _service(user_repo, identity_repo)

    async def flow():
        first = await service.authenticate_external(PROVIDER, "7")
        second = await service.authenticate_external(PROVIDER, "7")

        assert first["user"]["id"] == second["user"]["id"]
        assert len(user_repo.rows) == 1
        assert len(identity_repo.rows) == 1

    asyncio.run(flow())


def test_distinct_provider_ids_create_distinct_users():
    user_repo = FakeRepo(model=User)
    identity_repo = FakeIdentityRepo(model=ExternalIdentity)
    service = _service(user_repo, identity_repo)

    async def flow():
        first = await service.authenticate_external(PROVIDER, "1")
        second = await service.authenticate_external(PROVIDER, "2")

        assert first["user"]["id"] != second["user"]["id"]
        assert len(user_repo.rows) == 2
        assert len(identity_repo.rows) == 2

    asyncio.run(flow())


def test_identity_without_user_raises_422():
    user_repo = FakeRepo(model=User)
    identity_repo = FakeIdentityRepo(model=ExternalIdentity)
    identity_repo.rows.append(
        ExternalIdentity(
            provider="telegram",
            provider_user_id="7",
            user_id=uuid.uuid4(),
        )
    )
    service = _service(user_repo, identity_repo)

    async def flow():
        with pytest.raises(ServiceError) as exc_info:
            await service.authenticate_external(PROVIDER, "7")
        assert exc_info.value.status_code == 422
        assert "User does not exist" in exc_info.value.message

    asyncio.run(flow())


def test_commit_race_after_rollback_returns_422():
    user_repo = FakeRepo(model=User)
    identity_repo = FakeIdentityRepo(model=ExternalIdentity)
    service = _service(
        user_repo,
        identity_repo,
        uow=ConstraintUnitOfWork(user_repo, identity_repo),
    )

    async def flow():
        with pytest.raises(ServiceError) as exc_info:
            await service.authenticate_external(PROVIDER, "7")
        assert exc_info.value.status_code == 422
        assert "User already exists" in exc_info.value.message

    asyncio.run(flow())


if __name__ == "__main__":
    for name, fn in sorted(globals().items()):
        if name.startswith("test_") and callable(fn):
            fn()
    print("external auth service tests passed")