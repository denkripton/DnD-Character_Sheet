import asyncio

from aio_pika import ExchangeType

from src.infrastructure.rabbitmq.topology import Topology


class FakeQueue:
    def __init__(self, name):
        self.name = name
        self.bindings = []

    async def bind(self, exchange, routing_key="", arguments=None):
        self.bindings.append((exchange, routing_key))


class FakeChannel:
    def __init__(self):
        self.exchanges = []
        self.queues = {}
        self.is_closed = False

    async def declare_exchange(self, name, type=ExchangeType.TOPIC, durable=True):
        self.exchanges.append((name, ExchangeType(type), durable))

    async def declare_queue(self, name, durable=True, arguments=None):
        queue = FakeQueue(name)
        queue.durable = durable
        queue.arguments = arguments or {}
        self.queues[name] = queue
        return queue


def make_topology():
    return Topology(
        exchange_name="dnd.events",
        queue_prefix="backend",
        exchange_type="topic",
    )


def test_topology_name_derivation():
    topology = make_topology()

    assert topology.exchange_name == "dnd.events"
    assert topology.dead_letter_exchange_name == "dnd.events.dlx"
    assert topology.retry_exchange_name == "dnd.events.retryx"
    assert topology.queue_name("updates") == "backend.updates"
    assert topology.dead_letter_queue_name("backend.updates") == "backend.updates.dlq"
    assert topology.retry_queue_name("backend.updates") == "backend.updates.retry"


def test_declare_creates_main_dead_letter_and_retry_exchanges():
    topology = make_topology()
    channel = FakeChannel()

    asyncio.run(topology.declare(channel))

    assert channel.exchanges == [
        ("dnd.events", ExchangeType.TOPIC, True),
        ("dnd.events.dlx", ExchangeType.FANOUT, True),
        ("dnd.events.retryx", ExchangeType.DIRECT, True),
    ]


def test_declare_queue_creates_dlq_bound_to_dead_letter_exchange():
    topology = make_topology()
    channel = FakeChannel()

    queue = asyncio.run(topology.declare_queue(channel, "backend.updates"))

    assert queue is channel.queues["backend.updates"]
    assert channel.queues["backend.updates"].durable is True
    assert channel.queues["backend.updates"].arguments == {
        "x-dead-letter-exchange": "dnd.events.dlx"
    }
    assert channel.queues["backend.updates.dlq"].durable is True
    assert channel.queues["backend.updates.dlq"].bindings == [
        ("dnd.events.dlx", "")
    ]


def test_declare_queue_creates_retry_queue_with_backoff_to_main_queue():
    topology = make_topology()
    channel = FakeChannel()

    asyncio.run(topology.declare_queue(channel, "backend.updates"))

    retry = channel.queues["backend.updates.retry"]
    assert retry.durable is True
    assert retry.arguments == {
        "x-message-ttl": 5000,
        "x-dead-letter-exchange": "dnd.events",
    }
    assert retry.bindings == [("dnd.events.retryx", "backend.updates")]