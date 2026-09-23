import asyncio
from uuid import uuid4

from app.config import BotConfig
from app.infrastructure.rabbitmq.client import BotRabbitMQClient
from app.messaging import (
    BOT_EVENTS_QUEUE,
    ROUTING_KEY_ALL_EVENTS,
    MessageType,
    create_message,
)
from src.messaging.contract import messaging_route


class FakeBus:
    def __init__(self):
        self.started = False
        self.closed = False
        self.published = []
        self.subscriptions = []

    async def start(self):
        self.started = True

    async def close(self):
        self.closed = True

    async def publish(self, envelope, routing_key):
        self.published.append((envelope, routing_key))

    async def subscribe(self, queue_name, routing_keys, handler):
        self.subscriptions.append((queue_name, list(routing_keys), handler))


def _config(**overrides):
    return BotConfig(BOT_TOKEN="12345:test-token", **overrides)


def test_start_subscribes_events_queue():
    bus = FakeBus()
    client = BotRabbitMQClient(_config(), bus=bus)
    asyncio.run(client.start())
    assert bus.started
    assert len(bus.subscriptions) == 1
    queue, keys, _ = bus.subscriptions[0]
    assert queue == f"bot.{BOT_EVENTS_QUEUE}"
    assert keys == [ROUTING_KEY_ALL_EVENTS]


def test_events_queue_respects_prefix():
    config = _config(BOT_RABBITMQ_QUEUE_PREFIX="assistant")
    client = BotRabbitMQClient(config, bus=FakeBus())
    assert client.events_queue == f"assistant.{BOT_EVENTS_QUEUE}"


def test_publish_command_builds_envelope():
    bus = FakeBus()
    client = BotRabbitMQClient(_config(), bus=bus)
    correlation_id = uuid4()
    envelope = asyncio.run(
        client.publish_command(
            MessageType.CHARACTER_GENERATE,
            {"user_id": 7},
            correlation_id=correlation_id,
        ),
    )
    assert envelope.type == MessageType.CHARACTER_GENERATE.value
    assert envelope.correlation_id == correlation_id
    assert envelope.payload == {"user_id": 7}
    (published, routing_key), = bus.published
    assert published is envelope
    assert routing_key == messaging_route(MessageType.CHARACTER_GENERATE)


def test_publish_command_uses_headers():
    bus = FakeBus()
    client = BotRabbitMQClient(_config(), bus=bus)
    asyncio.run(client.publish_command(MessageType.CHARACTER_GET, headers={"source": "telegram"}))
    (envelope, _), = bus.published
    assert envelope.headers == {"source": "telegram"}


def test_close_leaves_injected_bus_open():
    bus = FakeBus()
    client = BotRabbitMQClient(_config(), bus=bus)
    asyncio.run(client.close())
    assert not bus.closed


def test_on_event_notifies_registered_handlers():
    bus = FakeBus()
    client = BotRabbitMQClient(_config(), bus=bus)
    seen = []

    async def record(envelope):
        seen.append(envelope)

    client.on_event(record)
    asyncio.run(client.start())
    (_, _, handler), = bus.subscriptions
    envelope = create_message(MessageType.CHARACTER_GENERATED, {"character_id": 1})
    asyncio.run(handler(envelope))
    assert seen == [envelope]