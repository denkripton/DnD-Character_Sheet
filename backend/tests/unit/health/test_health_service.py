import asyncio
from contextlib import asynccontextmanager
from types import SimpleNamespace

from redis.exceptions import ConnectionError as RedisConnectionError
from sqlalchemy.exc import SQLAlchemyError
from src.config import settings
from src.modules.health.service import (
    HealthService,
    check_postgres,
    check_rabbitmq,
    check_redis,
)
from tests.utils import FakeRedis


class FakeConnection:
    def __init__(self, error=None):
        self.error = error

    async def execute(self, statement):
        if self.error is not None:
            raise self.error


def make_engine(error=None):
    @asynccontextmanager
    async def connect():
        yield FakeConnection(error)

    return SimpleNamespace(connect=connect)


def make_slow_engine():
    @asynccontextmanager
    async def connect():
        await asyncio.sleep(1)
        yield FakeConnection()

    return SimpleNamespace(connect=connect)


class FakeBus:
    def __init__(self, healthy=True, error=None):
        self.healthy = healthy
        self.error = error

    async def health_check(self):
        if self.error is not None:
            raise self.error
        return self.healthy


def run(coro):
    return asyncio.run(coro)


def test_check_postgres_up():
    assert run(check_postgres(make_engine())) == "up"


def test_check_postgres_down_on_driver_error():
    error = SQLAlchemyError("connection refused")

    assert run(check_postgres(make_engine(error))) == "down"


def test_check_postgres_never_returns_error_details():
    error = SQLAlchemyError(
        "postgresql+asyncpg://app:change_me@db:5432/app connection failed"
    )

    result = run(check_postgres(make_engine(error)))

    assert result == "down"
    assert "change_me" not in result


def test_check_postgres_down_on_timeout(monkeypatch):
    monkeypatch.setattr(settings, "HEALTH_CHECK_TIMEOUT_SECONDS", 0.05)

    assert run(check_postgres(make_slow_engine())) == "down"


def test_check_redis_up():
    assert run(check_redis(FakeRedis())) == "up"


def test_check_redis_down():
    assert run(check_redis(FakeRedis(fail=True))) == "down"


def test_check_redis_down_on_redis_client_error():
    class BrokenRedis:
        async def ping(self):
            raise RedisConnectionError("Error 111 connecting to redis:6379.")

    assert run(check_redis(BrokenRedis())) == "down"


def test_check_rabbitmq_up():
    assert run(check_rabbitmq(FakeBus(healthy=True))) == "up"


def test_check_rabbitmq_down_when_connection_is_not_healthy():
    assert run(check_rabbitmq(FakeBus(healthy=False))) == "down"


def test_check_rabbitmq_down_on_error():
    bus = FakeBus(error=ConnectionError("broker down"))

    assert run(check_rabbitmq(bus)) == "down"


def test_readiness_reports_ready_when_all_dependencies_are_up():
    service = HealthService(
        engine=make_engine(),
        redis_client=FakeRedis(),
        message_bus=FakeBus(),
    )

    result = run(service.readiness())

    assert result.status == "ready"
    assert result.checks == {"postgres": "up", "redis": "up", "rabbitmq": "up"}


def test_readiness_reports_not_ready_when_one_dependency_is_down():
    service = HealthService(
        engine=make_engine(),
        redis_client=FakeRedis(fail=True),
        message_bus=FakeBus(),
    )

    result = run(service.readiness())

    assert result.status == "not_ready"
    assert result.checks == {"postgres": "up", "redis": "down", "rabbitmq": "up"}
