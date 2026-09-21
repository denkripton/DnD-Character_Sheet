from uuid import UUID, uuid4

from src.infrastructure.rabbitmq.consumer import RabbitMQConsumer
from src.infrastructure.rabbitmq.serialization import serialize
from src.infrastructure.rabbitmq.topology import Topology
from src.messaging.enums.constants import RETRY_COUNT_HEADER
from src.messaging.messages import MessageEnvelope


class FakePublisher:
    def __init__(self):
        self.retried = []

    async def publish_retry(self, envelope, routing_key, retry_count):
        self.retried.append((envelope, routing_key, retry_count))


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

    async def ack(self):
        self.acked = True

    async def reject(self, requeue=True):
        self.rejected = True
        self.rejected_requeue = requeue


def make_consumer(max_retries=3):
    publisher = FakePublisher()
    consumer = RabbitMQConsumer(
        connection=object(),
        topology=Topology("dnd.events", "backend"),
        max_retries=max_retries,
    )
    consumer._publisher = publisher
    return consumer, publisher


def deliver(retry_count=None):
    envelope = MessageEnvelope(
        type="character.updated",
        payload={"character_id": 42},
    )
    body = serialize(envelope)
    headers = {"source": "bot"}
    if retry_count is not None:
        headers = {**headers, RETRY_COUNT_HEADER: str(retry_count)}
    message = FakeIncomingMessage(
        body=body,
        message_id=str(envelope.message_id),
        correlation_id=str(uuid4()),
        headers=headers,
        type="character.updated",
    )
    return envelope, message


def run(processor, message):
    import asyncio

    return asyncio.run(processor(message))


def test_to_envelope_reconstructs_envelope_from_incoming_message():
    consumer, _ = make_consumer()
    envelope, message = deliver()

    restored = consumer._to_envelope(message)

    assert restored.type == "character.updated"
    assert restored.message_id == envelope.message_id
    assert restored.correlation_id is not None
    assert restored.headers == {"source": "bot"}
    assert restored.payload == {"character_id": 42}


def test_processor_acks_on_successful_handling():
    consumer, _ = make_consumer()
    envelope, message = deliver()
    handled = []

    async def handler(envelope):
        handled.append(envelope)

    run(consumer._make_processor(handler, "backend.updates"), message)

    assert message.acked is True
    assert message.rejected is False
    delivered_envelope = handled[0]
    assert delivered_envelope.message_id == envelope.message_id
    assert delivered_envelope.correlation_id == UUID(message.correlation_id)
    assert delivered_envelope.headers == {"source": "bot"}
    assert delivered_envelope.payload == {"character_id": 42}


def test_processor_republishes_to_retry_on_failed_handling():
    consumer, publisher = make_consumer()
    _, message = deliver()

    async def handler(envelope):
        raise RuntimeError("boom")

    run(consumer._make_processor(handler, "backend.updates"), message)

    expected = consumer._to_envelope(message)
    assert publisher.retried == [(expected, "backend.updates", 1)]
    assert message.acked is True
    assert message.rejected is False


def test_processor_increments_retry_count_on_following_failures():
    consumer, publisher = make_consumer()
    _, message = deliver(retry_count=1)

    async def handler(envelope):
        raise RuntimeError("boom")

    run(consumer._make_processor(handler, "backend.updates"), message)

    expected = consumer._to_envelope(message)
    assert publisher.retried == [(expected, "backend.updates", 2)]
    assert message.acked is True
    assert message.rejected is False


def test_processor_dead_letters_after_max_retries():
    consumer, publisher = make_consumer(max_retries=3)
    _, message = deliver(retry_count=3)

    async def handler(envelope):
        raise RuntimeError("boom")

    run(consumer._make_processor(handler, "backend.updates"), message)

    assert publisher.retried == []
    assert message.rejected is True
    assert message.rejected_requeue is False
    assert message.acked is False


def test_processor_rejects_malformed_body_without_retry():
    consumer, publisher = make_consumer()
    message = FakeIncomingMessage(body=b"not-json")
    handled = []

    async def handler(envelope):
        handled.append(envelope)

    run(consumer._make_processor(handler, "backend.updates"), message)

    assert publisher.retried == []
    assert message.rejected is True
    assert message.rejected_requeue is False
    assert message.acked is False
    assert handled == []