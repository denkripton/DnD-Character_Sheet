from aio_pika import ExchangeType
from aio_pika.abc import AbstractChannel, AbstractQueue

from src.messaging.constants import (
    DEAD_LETTER_ARGUMENT,
    DEAD_LETTER_EXCHANGE_SUFFIX,
    DEAD_LETTER_QUEUE_SUFFIX,
)


class Topology:
    def __init__(
        self,
        exchange_name: str,
        queue_prefix: str,
        exchange_type: str = "topic",
    ):
        self.exchange_name = exchange_name
        self.queue_prefix = queue_prefix
        self.exchange_type = exchange_type

    @property
    def dead_letter_exchange_name(self) -> str:
        return f"{self.exchange_name}{DEAD_LETTER_EXCHANGE_SUFFIX}"

    def queue_name(self, name: str) -> str:
        return f"{self.queue_prefix}.{name}"

    def dead_letter_queue_name(self, queue_name: str) -> str:
        return f"{queue_name}{DEAD_LETTER_QUEUE_SUFFIX}"

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

    async def declare_queue(self, channel: AbstractChannel, name: str) -> AbstractQueue:
        queue = await channel.declare_queue(
            name,
            durable=True,
            arguments={DEAD_LETTER_ARGUMENT: self.dead_letter_exchange_name},
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