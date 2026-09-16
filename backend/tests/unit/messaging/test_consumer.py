from uuid import UUID, uuid4

import pytest

from src.infrastructure.rabbitmq.consumer import RabbitMQConsumer
from src.infrastructure.rabbitmq.serialization import serialize
from src.infrastructure.rabbitmq.topology import Topology
from src.messaging.messages import MessageEnvelope
from src.utils.exceptions.serialization import SerializationError


class FakeProcess:
    def __init__(self, requeue, fake):
        self.requeue = requeue
        self.fake = fake

    async def __aenter__(self):
        return self

    async def __aexit__(self, exc_type, exc, traceback):
        if exc_type is None:
            self.fake.acked = True
        else:
            self.fake.rejected = True
            self.fake.rejected_requeue = self.requeue
        return False


class FakeIncomingMessage:
    def __init__(self, body, message_id=None, correlation_id=None, headers=None, type=None):
        self.body = body
        self.message_id = message_id
        self.correlation_id = correlation_id
        self.headers = headers or {}
        self.type = type
        self.acked = False
        self.rejected = False
        self.rejected_requeue = None

    def process(self, requeue=True):
        return FakeProcess(requeue, self)


def make_consumer():
    return RabbitMQConsumer(
        connection=object(),
        topology=Topology("dnd.events", "backend"),
    )


def deliver():
    envelope = MessageEnvelope(
        type="character.updated",
        payload={"character_id": 42},
    )
    body = serialize(envelope)
    message = FakeIncomingMessage(
        body=body,
        message_id=str(envelope.message_id),
        correlation_id=str(uuid4()),
        headers={"source": "bot"},
        type="character.updated",
    )
    return envelope, message


def test_to_envelope_reconstructs_envelope_from_incoming_message():
    consumer = make_consumer()
    envelope, message = deliver()

    restored = consumer._to_envelope(message)

    assert restored.type == "character.updated"
    assert restored.message_id == envelope.message_id
    assert restored.correlation_id is not None
    assert restored.headers == {"source": "bot"}
    assert restored.payload == {"character_id": 42}


def test_processor_acks_on_successful_handling():
    consumer = make_consumer()
    envelope, message = deliver()
    handled = []

    async def handler(envelope):
        handled.append(envelope)

    processor = consumer._make_processor(handler)
    asyncio_run(processor(message))

    assert message.acked is True
    assert message.rejected is False
    assert len(handled) == 1
    delivered_envelope = handled[0]
    assert delivered_envelope.message_id == envelope.message_id
    assert delivered_envelope.correlation_id == UUID(message.correlation_id)
    assert delivered_envelope.headers == {"source": "bot"}
    assert delivered_envelope.type == "character.updated"
    assert delivered_envelope.payload == {"character_id": 42}


def test_processor_dead_letters_on_failed_handling():
    consumer = make_consumer()
    _, message = deliver()

    async def handler(envelope):
        raise RuntimeError("boom")

    processor = consumer._make_processor(handler)

    with pytest.raises(RuntimeError):
        asyncio_run(processor(message))

    assert message.rejected is True
    assert message.rejected_requeue is False
    assert message.acked is False


def test_processor_dead_letters_malformed_body():
    consumer = make_consumer()
    message = FakeIncomingMessage(body=b"not-json")
    handled = []

    async def handler(envelope):
        handled.append(envelope)

    processor = consumer._make_processor(handler)

    with pytest.raises(SerializationError):
        asyncio_run(processor(message))

    assert message.rejected is True
    assert message.rejected_requeue is False
    assert handled == []


def asyncio_run(coro):
    import asyncio

    return asyncio.run(coro)