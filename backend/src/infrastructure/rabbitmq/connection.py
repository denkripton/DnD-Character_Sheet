import asyncio
import logging

import aio_pika
from aio_pika.abc import AbstractChannel

from src.utils.exceptions.connection import RabbitMQConnectionError

logger = logging.getLogger(__name__)


class RabbitMQConnection:
    def __init__(
        self,
        url: str,
        reconnect_interval_seconds: float = 5.0,
    ):
        self._url = url
        self._reconnect_interval_seconds = reconnect_interval_seconds
        self._connection = None

    @property
    def is_connected(self) -> bool:
        return self._connection is not None and not self._connection.is_closed

    async def connect(self) -> None:
        while True:
            if self.is_connected:
                return
            self._connection = None
            try:
                self._connection = await aio_pika.connect_robust(self._url)
            except (TimeoutError, OSError, aio_pika.exceptions.AMQPError) as exc:
                logger.warning(
                    "RabbitMQ connection failed (%s); retrying in %ss",
                    exc,
                    self._reconnect_interval_seconds,
                )
                await asyncio.sleep(self._reconnect_interval_seconds)
            else:
                logger.info("RabbitMQ connected")
                return

    async def channel(self) -> AbstractChannel:
        await self.connect()
        if self._connection is None:
            raise RabbitMQConnectionError("RabbitMQ is not connected")
        return await self._connection.channel()

    async def close(self) -> None:
        connection, self._connection = self._connection, None
        if connection is not None and not connection.is_closed:
            await connection.close()