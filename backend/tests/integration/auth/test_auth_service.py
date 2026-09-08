import asyncio

import pytest

from src.exceptions import ServiceError
from src.modules.auth.models import User
from src.modules.auth.schemas.user.creation import UserCreateSchema
from src.modules.auth.schemas.user.login import UserLoginSchema
from src.modules.auth.service import UserService
from src.modules.auth.utils import pw_manager
from src.modules.auth.utils.jwt_actions import JWT
from tests.utils import FakeRepo


def _build():
    user_repo = FakeRepo(model=User)
    service = UserService(user_repository=user_repo, jwt=JWT())
    return service, user_repo


def _create_schema(email="johndoe@gmail.com", password="som@Th1ng"):
    return UserCreateSchema(username="John", email=email, password=password)


def _login_schema(email="johndoe@gmail.com", password="som@Th1ng"):
    return UserLoginSchema(email=email, password=password)


def test_register_hashes_password():
    service, user_repo = _build()

    async def flow():
        user = await service.register(_create_schema())
        assert user.email == "johndoe@gmail.com"
        assert isinstance(user.password, bytes)
        assert user.password != b"som@Th1ng"
        assert pw_manager.check_password("som@Th1ng", user.password) is True
        assert len(user_repo.rows) == 1

    asyncio.run(flow())


def test_register_duplicate_email_raises():
    service, _ = _build()

    async def flow():
        await service.register(_create_schema())
        with pytest.raises(ServiceError) as exc_info:
            await service.register(_create_schema())
        assert exc_info.value.status_code == 422

    asyncio.run(flow())


def test_login_returns_tokens():
    service, _ = _build()

    async def flow():
        await service.register(_create_schema())
        tokens = await service.login(_login_schema())
        assert "access" in tokens
        assert "refresh" in tokens
        assert tokens["access"] != tokens["refresh"]

    asyncio.run(flow())


def test_login_wrong_password_raises():
    service, _ = _build()

    async def flow():
        await service.register(_create_schema())
        with pytest.raises(ServiceError) as exc_info:
            await service.login(_login_schema(password="WrongPass1!"))
        assert exc_info.value.status_code == 403

    asyncio.run(flow())


def test_login_missing_user_raises():
    service, _ = _build()

    async def flow():
        with pytest.raises(ServiceError) as exc_info:
            await service.login(_login_schema())
        assert exc_info.value.status_code == 422

    asyncio.run(flow())


if __name__ == "__main__":
    for name, fn in sorted(globals().items()):
        if name.startswith("test_") and callable(fn):
            fn()
    print("auth service tests passed")