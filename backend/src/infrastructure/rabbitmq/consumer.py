from collections.abc import Awaitable, Callable, Sequence

from aio_pika.abc import AbstractChannel, AbstractIncomingMessage

from src.infrastructure.rabbitmq.connection import RabbitMQConnection
from src.infrastructure.rabbitmq.publisher import RabbitMQPublisher
from src.infrastructure.rabbitmq.topology import Topology
from src.infrastructure.rabbitmq.utils import properties_from_message, to_envelope
from src.messaging.enums.constants import RETRY_COUNT_HEADER
from src.messaging.interfaces import MessageConsumer, MessageHandler
from src.messaging.messages import MessageEnvelope
from src.utils.exceptions import SerializationError


class RabbitMQConsumer(MessageConsumer):
    def __init__(
        self,
        connection: RabbitMQConnection,
        topology: Topology,
        prefetch_count: int = 10,
        max_retries: int = 3,
    ):
        self._connection = connection
        self._topology = topology
        self._prefetch_count = prefetch_count
        self._max_retries = max_retries
        self._publisher = RabbitMQPublisher(connection=connection, topology=topology)
        self._channel: AbstractChannel | None = None
        self._channel_cm = None

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
        await queue.consume(self._make_processor(handler, queue_name))

    def _make_processor(
        self,
        handler: MessageHandler,
        queue_name: str,
    ) -> Callable[[AbstractIncomingMessage], Awaitable[None]]:
        async def process(message: AbstractIncomingMessage) -> None:
            try:
                envelope = self._to_envelope(message)
            except SerializationError:
                await message.reject(requeue=False)
                return
            try:
                await handler(envelope)
            except Exception:
                failed_attempts = int(
                    (message.headers or {}).get(RETRY_COUNT_HEADER, 0) or 0
                )
                if failed_attempts < self._max_retries:
                    await self._publisher.publish_retry(
                        envelope,
                        queue_name,
                        failed_attempts + 1,
                    )
                    await message.ack()
                else:
                    await message.reject(requeue=False)
                return
            await message.ack()

        return process

    def _to_envelope(self, message: AbstractIncomingMessage) -> MessageEnvelope:
        return to_envelope(message.body, properties_from_message(message))

    async def _ensure_channel(self) -> AbstractChannel:
        if self._channel is not None and not self._channel.is_closed:
            return self._channel
        channel_cm = self._connection.channel()
        channel = await channel_cm.__aenter__()
        await channel.set_qos(prefetch_count=self._prefetch_count)
        self._channel_cm, self._channel = channel_cm, channel
        return channel

    async def close(self) -> None:
        channel_cm, self._channel_cm = self._channel_cm, None
        self._channel = None
        if channel_cm is not None:
            await channel_cm.__aexit__(None, None, None)