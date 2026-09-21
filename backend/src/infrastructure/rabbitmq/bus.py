from collections.abc import Sequence

from src.infrastructure.rabbitmq.connection import RabbitMQConnection
from src.infrastructure.rabbitmq.consumer import RabbitMQConsumer
from src.infrastructure.rabbitmq.publisher import RabbitMQPublisher
from src.infrastructure.rabbitmq.topology import Topology
from src.messaging.interfaces import MessageBus, MessageHandler
from src.messaging.messages import MessageEnvelope


class RabbitMQMessageBus(MessageBus):
    def __init__(
        self,
        connection: RabbitMQConnection,
        topology: Topology,
        prefetch_count: int = 10,
        max_retries: int = 3,
    ):
        self._connection = connection
        self._topology = topology
        self._publisher = RabbitMQPublisher(connection=connection, topology=topology)
        self._consumer = RabbitMQConsumer(
            connection=connection,
            topology=topology,
            prefetch_count=prefetch_count,
            max_retries=max_retries,
        )

    async def start(self) -> None:
        await self._connection.connect()
        async with self._connection.channel() as channel:
            await self._topology.declare(channel)

    async def close(self) -> None:
        await self._consumer.close()
        await self._connection.close()

    async def publish(self, envelope: MessageEnvelope, routing_key: str) -> None:
        await self._publisher.publish(envelope, routing_key)

    async def subscribe(
        self,
        queue_name: str,
        routing_keys: Sequence[str],
        handler: MessageHandler,
    ) -> None:
        await self._consumer.subscribe(queue_name, routing_keys, handler)