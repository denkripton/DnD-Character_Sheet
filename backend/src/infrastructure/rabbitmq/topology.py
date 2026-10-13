from aio_pika import ExchangeType
from aio_pika.abc import AbstractChannel, AbstractQueue

from src.messaging.enums.constants import RabbitMQArgument, TopologySuffix


class Topology:
    def __init__(
        self,
        exchange_name: str,
        queue_prefix: str,
        exchange_type: str = "topic",
        retry_delay_seconds: float = 5.0,
    ):
        self.exchange_name = exchange_name
        self.queue_prefix = queue_prefix
        self.exchange_type = exchange_type
        self.retry_delay_seconds = retry_delay_seconds

    @property
    def dead_letter_exchange_name(self) -> str:
        return f"{self.exchange_name}{TopologySuffix.DEAD_LETTER_EXCHANGE.value}"

    @property
    def retry_exchange_name(self) -> str:
        return f"{self.exchange_name}{TopologySuffix.RETRY_EXCHANGE.value}"

    def queue_name(self, name: str) -> str:
        return f"{self.queue_prefix}.{name}"

    def dead_letter_queue_name(self, queue_name: str) -> str:
        return f"{queue_name}{TopologySuffix.DEAD_LETTER_QUEUE.value}"

    def retry_queue_name(self, queue_name: str) -> str:
        return f"{queue_name}{TopologySuffix.RETRY_QUEUE.value}"

    async def declare(self, channel: AbstractChannel) -> None:
        await channel.declare_exchange(
            self.exchange_name,
            ExchangeType(self.exchange_type),
            durable=True,
        )
        await channel.declare_exchange(
            self.dead_letter_exchange_name,
            ExchangeType.FANOUT,
            durable=True,
        )
        await channel.declare_exchange(
            self.retry_exchange_name,
            ExchangeType.DIRECT,
            durable=True,
        )

    async def declare_queue(self, channel: AbstractChannel, name: str) -> AbstractQueue:
        queue = await channel.declare_queue(
            name,
            durable=True,
            arguments={
                RabbitMQArgument.DEAD_LETTER_EXCHANGE.value: self.dead_letter_exchange_name
            },
        )
        retry_queue = await channel.declare_queue(
            self.retry_queue_name(name),
            durable=True,
            arguments={
                RabbitMQArgument.MESSAGE_TTL.value: int(
                    self.retry_delay_seconds * 1000
                ),
                RabbitMQArgument.DEAD_LETTER_EXCHANGE.value: self.exchange_name,
            },
        )
        await retry_queue.bind(
            self.retry_exchange_name,
            routing_key=name,
        )
        dead_letter_queue = await channel.declare_queue(
            self.dead_letter_queue_name(name),
            durable=True,
        )
        await dead_letter_queue.bind(
            self.dead_letter_exchange_name,
            routing_key="",
        )
        return queue
