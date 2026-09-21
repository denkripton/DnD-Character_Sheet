import asyncio

import pytest

from src.infrastructure.rabbitmq.connection import RabbitMQConnection
from src.utils.exceptions import RabbitMQConnectionError


class FakeChannel:
    def __init__(self):
        self.is_closed = False

    async def close(self):
        self.is_closed = True


class FakeBrokerConnection:
    def __init__(self):
        self.is_closed = False
        self.closed = False

    async def close(self):
        self.is_closed = True
        self.closed = True

    async def channel(self):
        return FakeChannel()


def run(coro):
    return asyncio.run(coro)


def flaky_factory(*results):
    attempts = []

    async def factory(url):
        attempts.append(url)
        result = results[len(attempts) - 1] if len(attempts) <= len(results) else None
        if isinstance(result, Exception):
            raise result
        return result or FakeBrokerConnection()

    return factory, attempts


def test_connect_retries_until_success():
    factory, attempts = flaky_factory(OSError("down"), TimeoutError("slow"))
    connection = RabbitMQConnection(
        url="amqp://guest:guest@localhost:5672/",
        reconnect_interval_seconds=0,
        connect_factory=factory,
    )

    run(connection.connect())

    assert connection.is_connected is True
    assert len(attempts) == 3


def test_connect_is_idempotent():
    factory, attempts = flaky_factory()
    connection = RabbitMQConnection(
        url="amqp://guest:guest@localhost:5672/",
        connect_factory=factory,
    )

    run(connection.connect())
    run(connection.connect())

    assert len(attempts) == 1


def test_channel_yields_a_channel_from_connection():
    factory, _ = flaky_factory()
    connection = RabbitMQConnection(
        url="amqp://guest:guest@localhost:5672/",
        connect_factory=factory,
    )

    async def scenario():
        async with connection.channel() as channel:
            assert isinstance(channel, FakeChannel)

    run(scenario())

    assert connection.is_connected is True


def test_close_tears_down_pool_and_connection():
    broker = FakeBrokerConnection()
    factory, _ = flaky_factory(broker)
    connection = RabbitMQConnection(
        url="amqp://guest:guest@localhost:5672/",
        connect_factory=factory,
    )
    run(connection.connect())

    run(connection.close())

    assert broker.closed is True
    assert connection.is_connected is False


def test_connect_after_close_raises():
    factory, _ = flaky_factory()
    connection = RabbitMQConnection(
        url="amqp://guest:guest@localhost:5672/",
        connect_factory=factory,
    )
    run(connection.connect())
    run(connection.close())

    with pytest.raises(RabbitMQConnectionError):
        run(connection.connect())