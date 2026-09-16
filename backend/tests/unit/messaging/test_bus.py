import asyncio
from unittest.mock import AsyncMock

from src.infrastructure.rabbitmq.bus import RabbitMQMessageBus
from src.messaging.messages import MessageEnvelope


class FakeConnection:
    def __init__(self):
        self.connected = False
        self.closed = False
        self.channels = []

    async def connect(self):
        self.connected = True

    async def close(self):
        self.closed = True

    async def channel(self):
        channel = FakeChannel()
        self.channels.append(channel)
        return channel


class FakeChannel:
    def __init__(self):
        self.is_closed = False

    async def close(self):
        self.is_closed = True


class FakeTopology:
    def __init__(self):
        self.declared = False

    async def declare(self, channel):
        self.declared = True


def make_bus():
    connection = FakeConnection()
    topology = FakeTopology()
    bus = RabbitMQMessageBus(
        connection=connection,
        topology=topology,
    )
    return bus, connection, topology


def test_start_connects_and_declares_topology():
    bus, connection, topology = make_bus()

    asyncio.run(bus.start())

    assert connection.connected is True
    assert topology.declared is True


def test_close_shuts_down_connection():
    bus, connection, _ = make_bus()
    asyncio.run(bus.start())

    asyncio.run(bus.close())

    assert connection.closed is True


def test_publish_delegates_to_publisher():
    bus, _, _ = make_bus()
    asyncio.run(bus.start())

    mock_publisher = AsyncMock()
    bus._publisher = mock_publisher
    envelope = MessageEnvelope(type="ping")

    asyncio.run(bus.publish(envelope, routing_key="character.events"))

    mock_publisher.publish.assert_awaited_once_with(envelope, "character.events")


def test_subscribe_delegates_to_consumer():
    bus, _, _ = make_bus()
    asyncio.run(bus.start())

    mock_consumer = AsyncMock()
    bus._consumer = mock_consumer
    handler = AsyncMock()

    asyncio.run(bus.subscribe("character.updates", ["characters.*"], handler))

    mock_consumer.subscribe.assert_awaited_once_with(
        "character.updates", ["characters.*"], handler
    )