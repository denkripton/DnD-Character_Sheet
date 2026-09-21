import asyncio
from contextlib import asynccontextmanager
from datetime import UTC, datetime
from uuid import uuid4

import pytest
from aio_pika import DeliveryMode
from pamqp.commands import Basic

from src.infrastructure.rabbitmq.publisher import RabbitMQPublisher
from src.infrastructure.rabbitmq.serialization import deserialize
from src.infrastructure.rabbitmq.topology import Topology
from src.messaging.enums.constants import (
    CONTENT_TYPE_JSON,
    RETRY_COUNT_HEADER,
)
from src.messaging.messages import MessageEnvelope
from src.utils.exceptions import RabbitMQMessagePublishError


class FakeExchange:
    def __init__(self, response=Basic.Ack):
        self.published = []
        self.response = response

    async def publish(self, message, routing_key, mandatory=True):
        self.published.append((message, routing_key, mandatory))
        return self.response


class FakeChannel:
    def __init__(self, response=Basic.Ack):
        self.exchanges = {}
        self.response = response
        self.is_closed = False

    async def declare_exchange(self, name, type, durable=True):
        exchange = self.exchanges.get(name)
        if exchange is None:
            exchange = FakeExchange(response=self.response)
            self.exchanges[name] = exchange
        return exchange


class FakeConnection:
    def __init__(self, response=Basic.Ack):
        self.channels = []
        self.response = response

    @asynccontextmanager
    async def channel(self):
        channel = FakeChannel(response=self.response)
        self.channels.append(channel)
        yield channel


def make_publisher():
    connection = FakeConnection()
    topology = Topology(
        exchange_name="dnd.events",
        queue_prefix="backend",
        exchange_type="topic",
    )
    publisher = RabbitMQPublisher(connection=connection, topology=topology)
    return publisher, connection, topology


def make_envelope():
    return MessageEnvelope(
        type="character.generate.command",
        message_id=uuid4(),
        correlation_id=uuid4(),
        timestamp=datetime(2026, 1, 2, 3, 4, 5, tzinfo=UTC),
        headers={"source": "bot"},
        payload={"user_id": 7},
    )


def run(coro):
    return asyncio.run(coro)


def test_publish_sends_persistent_message_to_main_exchange():
    publisher, connection, _ = make_publisher()
    envelope = make_envelope()

    run(publisher.publish(envelope, "commands.character.generate"))

    channel = connection.channels[0]
    exchange = channel.exchanges["dnd.events"]
    (message, routing_key, mandatory) = exchange.published[0]
    assert routing_key == "commands.character.generate"
    assert mandatory is True
    assert message.content_type == CONTENT_TYPE_JSON
    assert message.delivery_mode == DeliveryMode.PERSISTENT
    assert message.message_id == str(envelope.message_id)
    assert message.correlation_id == str(envelope.correlation_id)
    assert message.timestamp == envelope.timestamp
    assert message.headers == {"source": "bot"}
    assert message.type == "character.generate.command"
    assert deserialize(message.body) == envelope


def test_publish_raises_when_broker_nacks():
    publisher, connection, _ = make_publisher()
    connection.response = Basic.Nack()

    with pytest.raises(RabbitMQMessagePublishError):
        run(publisher.publish(make_envelope(), "commands.character.generate"))


def test_publish_retry_routes_to_retry_exchange_with_count_header():
    publisher, connection, topology = make_publisher()
    envelope = make_envelope()

    run(publisher.publish_retry(envelope, "backend.bot_commands", 2))

    channel = connection.channels[0]
    assert list(channel.exchanges) == [topology.retry_exchange_name]
    exchange = channel.exchanges[topology.retry_exchange_name]
    (message, routing_key, _) = exchange.published[0]
    assert routing_key == "backend.bot_commands"
    assert message.headers == {"source": "bot", RETRY_COUNT_HEADER: "2"}
    restored = deserialize(message.body)
    assert restored.message_id == envelope.message_id
    assert restored.correlation_id == envelope.correlation_id
    assert restored.headers == {"source": "bot", RETRY_COUNT_HEADER: "2"}