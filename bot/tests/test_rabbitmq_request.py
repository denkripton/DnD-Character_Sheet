import asyncio

from app.config import BotConfig
from app.infrastructure.rabbitmq.client import BotRabbitMQClient
from app.messaging import (
    BOT_EVENTS_QUEUE,
    ROUTING_KEY_ALL_EVENTS,
    MessageType,
    create_message,
)


class FakeBus:
    def __init__(self, publish_error=None):
        self.published = []
        self.subscriptions = []
        self.publish_error = publish_error

    async def start(self):
        pass

    async def close(self):
        pass

    async def publish(self, envelope, routing_key):
        if self.publish_error is not None:
            raise self.publish_error
        self.published.append((envelope, routing_key))

    async def subscribe(self, queue_name, routing_keys, handler):
        self.subscriptions.append((queue_name, list(routing_keys), handler))


def _client(bus):
    config = BotConfig(BOT_TOKEN="12345:test-token")
    return BotRabbitMQClient(config, bus=bus)


def test_request_returns_correlated_response():
    async def flow():
        bus = FakeBus()
        client = _client(bus)
        await client.start()

        task = asyncio.create_task(
            client.request(MessageType.CHARACTER_CREATE, {}, timeout=5)
        )
        await asyncio.sleep(0.01)

        (command, _), = bus.published
        assert command.correlation_id is not None
        queue, keys, handler = bus.subscriptions[0]
        assert queue == f"bot.{BOT_EVENTS_QUEUE}"
        assert keys == [ROUTING_KEY_ALL_EVENTS]

        response = create_message(
            MessageType.CHARACTER_CREATED,
            {"ok": True},
            correlation_id=command.correlation_id,
        )
        await handler(response)
        result = await task
        assert result is response

    asyncio.run(flow())


def test_request_ignores_uncorrelated_events():
    async def flow():
        bus = FakeBus()
        client = _client(bus)
        await client.start()

        task = asyncio.create_task(
            client.request(MessageType.CHARACTER_CREATE, {}, timeout=0.05)
        )
        await asyncio.sleep(0.01)

        _, _, handler = bus.subscriptions[0]
        await handler(create_message(MessageType.CHARACTER_CREATED, {"ok": True}))

        try:
            await task
        except TimeoutError:
            return True
        return False

    assert asyncio.run(flow())


def test_request_times_out_without_response():
    async def flow():
        bus = FakeBus()
        client = _client(bus)
        await client.start()
        try:
            await client.request(MessageType.CHARACTER_CREATE, {}, timeout=0.01)
        except TimeoutError:
            return True
        return False

    assert asyncio.run(flow())


def test_request_propagates_publish_failure():
    async def flow():
        bus = FakeBus(publish_error=ConnectionError("broker down"))
        client = _client(bus)
        await client.start()
        try:
            await client.request(MessageType.CHARACTER_CREATE, {}, timeout=1)
        except ConnectionError:
            return True
        return False

    assert asyncio.run(flow())


def test_request_cleans_pending_after_timeout():
    async def flow():
        bus = FakeBus()
        client = _client(bus)
        await client.start()
        try:
            await client.request(MessageType.CHARACTER_CREATE, {}, timeout=0.01)
        except TimeoutError:
            pass
        return client._pending

    assert asyncio.run(flow()) == {}


def test_request_signs_command_when_secret_configured():
    from src.messaging.security import verify_command

    async def flow():
        bus = FakeBus()
        config = BotConfig(BOT_TOKEN="12345:test-token", BOT_API_SECRET="shared-secret")
        client = BotRabbitMQClient(config, bus=bus)
        await client.start()

        task = asyncio.create_task(
            client.request(
                MessageType.CHARACTER_CREATE,
                {},
                timeout=5,
                provider="telegram",
                provider_user_id="7",
                user_id="user-1",
            )
        )
        await asyncio.sleep(0.01)
        (command, _), = bus.published
        verify_command(command, "shared-secret")

        response = create_message(
            MessageType.CHARACTER_CREATED,
            {"ok": True},
            correlation_id=command.correlation_id,
        )
        _, _, handler = bus.subscriptions[0]
        await handler(response)
        await task

    asyncio.run(flow())
