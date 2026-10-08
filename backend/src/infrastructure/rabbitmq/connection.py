import asyncio
from collections.abc import Awaitable, Callable
from contextlib import asynccontextmanager

import aio_pika
import structlog
from aio_pika.abc import AbstractChannel, AbstractConnection
from aio_pika.pool import Pool

from src.utils.exceptions import RabbitMQConnectionError

ConnectionFactory = Callable[[str], Awaitable[AbstractConnection]]


class RabbitMQConnection:
    def __init__(
        self,
        url: str,
        reconnect_interval_seconds: float = 5.0,
        connect_factory: ConnectionFactory = aio_pika.connect_robust,
        max_channel_pool_size: int = 20,
    ):
        self._url = url
        self._reconnect_interval_seconds = reconnect_interval_seconds
        self._connect_factory = connect_factory
        self._max_channel_pool_size = max_channel_pool_size
        self._connection: AbstractConnection | None = None
        self._channel_pool: Pool[AbstractChannel] | None = None
        self._closed = False

    @property
    def is_connected(self) -> bool:
        return self._connection is not None and not self._connection.is_closed

    async def connect(self) -> None:
        if self._closed:
            raise RabbitMQConnectionError("RabbitMQ connection is closed")
        while not self.is_connected:
            if self._connection is not None:
                self._channel_pool = None
                self._connection = None
            try:
                self._connection = await self._connect_factory(self._url)
            except (TimeoutError, OSError, aio_pika.exceptions.AMQPError) as exc:
                structlog.get_logger(__name__).warning(
                    "rabbitmq_connection_failed",
                    error=str(exc),
                    reconnect_interval_seconds=self._reconnect_interval_seconds,
                )
                await asyncio.sleep(self._reconnect_interval_seconds)
            else:
                self._channel_pool = Pool(
                    self._open_channel,
                    max_size=self._max_channel_pool_size,
                )
                structlog.get_logger(__name__).info("rabbitmq_connected")

    async def _open_channel(self) -> AbstractChannel:
        if self._connection is None:
            raise RabbitMQConnectionError("RabbitMQ is not connected")
        return await self._connection.channel()

    @asynccontextmanager
    async def channel(self):
        await self.connect()
        if self._channel_pool is None:
            raise RabbitMQConnectionError("RabbitMQ is not connected")
        async with self._channel_pool.acquire() as channel:
            yield channel

    async def health_check(self) -> bool:
        if not self.is_connected or self._connection is None:
            structlog.get_logger(__name__).warning(
                "rabbitmq_health_check_failed",
                error_type="Disconnected",
            )
            return False
        try:
            channel = await self._connection.channel()
            await channel.close()
        except (OSError, aio_pika.exceptions.AMQPError) as exc:
            structlog.get_logger(__name__).warning(
                "rabbitmq_health_check_failed",
                error_type=type(exc).__name__,
                error=str(exc),
            )
            return False
        return True

    async def close(self) -> None:
        self._closed = True
        channel_pool, self._channel_pool = self._channel_pool, None
        if channel_pool is not None and not channel_pool.is_closed:
            await channel_pool.close()
        connection, self._connection = self._connection, None
        if connection is not None and not connection.is_closed:
            await connection.close()