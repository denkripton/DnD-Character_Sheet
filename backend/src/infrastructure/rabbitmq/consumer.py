from collections.abc import Awaitable, Callable, Sequence

from aio_pika.abc import AbstractChannel, AbstractIncomingMessage

from src.infrastructure.rabbitmq.connection import RabbitMQConnection
from src.infrastructure.rabbitmq.topology import Topology
from src.infrastructure.rabbitmq.utils import properties_from_message, to_envelope
from src.messaging.interfaces import MessageConsumer, MessageHandler
from src.messaging.messages import MessageEnvelope


class RabbitMQConsumer(MessageConsumer):
    def __init__(
        self,
        connection: RabbitMQConnection,
        topology: Topology,
        prefetch_count: int = 10,
    ):
        self._connection = connection
        self._topology = topology
        self._prefetch_count = prefetch_count
        self._channel: AbstractChannel | None = None

    async def subscribe(
        self,
        queue_name: str,
        routing_keys: Sequence[str],
        handler: MessageHandler,
    ) -> None:
        channel = await self._ensure_channel()
        queue = await self._topology.declare_queue(channel, queue_name)
        for routing_key in routing_keys:
            await queue.bind(
                self._topology.exchange_name,
                routing_key=routing_key,
            )
        await queue.consume(self._make_processor(handler))

    def _make_processor(
        self,
        handler: MessageHandler,
    ) -> Callable[[AbstractIncomingMessage], Awaitable[None]]:
        async def process(message: AbstractIncomingMessage) -> None:
            async with message.process(requeue=False):
                await handler(self._to_envelope(message))

        return process

    def _to_envelope(self, message: AbstractIncomingMessage) -> MessageEnvelope:
        return to_envelope(message.body, properties_from_message(message))

    async def _ensure_channel(self) -> AbstractChannel:
        if self._channel is not None and not self._channel.is_closed:
            return self._channel
        channel = await self._connection.channel()
        await channel.set_qos(prefetch_count=self._prefetch_count)
        self._channel = channel
        return channel

    async def close(self) -> None:
        channel, self._channel = self._channel, None
        if channel is not None and not channel.is_closed:
            await channel.close()