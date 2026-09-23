from uuid import UUID

import structlog
from src.infrastructure.rabbitmq.bus import RabbitMQMessageBus
from src.infrastructure.rabbitmq.connection import RabbitMQConnection
from src.infrastructure.rabbitmq.topology import Topology
from src.messaging.interfaces import MessageBus

from app.config import BotConfig
from app.messaging import (
    BOT_EVENTS_QUEUE,
    ROUTING_KEY_ALL_EVENTS,
    MessageEnvelope,
    MessageHandler,
    MessageType,
    create_message,
    messaging_route,
)


class BotRabbitMQClient:
    def __init__(self, config: BotConfig, bus: MessageBus | None = None):
        self._config = config
        self._owns_bus = bus is None
        self._event_handlers: list[MessageHandler] = []
        if bus is not None:
            self._bus = bus
        else:
            connection = RabbitMQConnection(
                url=config.RABBITMQ_URL,
                reconnect_interval_seconds=config.RABBITMQ_RECONNECT_INTERVAL_SECONDS,
            )
            topology = Topology(
                exchange_name=config.RABBITMQ_EXCHANGE,
                queue_prefix=config.BOT_RABBITMQ_QUEUE_PREFIX,
                exchange_type=config.RABBITMQ_EXCHANGE_TYPE,
                retry_delay_seconds=config.RABBITMQ_RETRY_DELAY_SECONDS,
            )
            self._bus = RabbitMQMessageBus(
                connection=connection,
                topology=topology,
                prefetch_count=config.RABBITMQ_PREFETCH_COUNT,
                max_retries=config.RABBITMQ_MAX_RETRIES,
            )
        self._logger = structlog.get_logger("app.rabbitmq")

    @property
    def bus(self) -> MessageBus:
        return self._bus

    @property
    def events_queue(self) -> str:
        return f"{self._config.BOT_RABBITMQ_QUEUE_PREFIX}.{BOT_EVENTS_QUEUE}"

    async def start(self) -> None:
        await self._bus.start()
        await self._subscribe_events()
        self._logger.info("rabbitmq_started", events_queue=self.events_queue)

    async def close(self) -> None:
        if self._owns_bus:
            await self._bus.close()
        self._logger.info("rabbitmq_stopped")

    def on_event(self, handler: MessageHandler) -> None:
        self._event_handlers.append(handler)

    async def publish_command(
        self,
        message_type: MessageType,
        payload=None,
        *,
        correlation_id: UUID | None = None,
        headers: dict[str, str] | None = None,
    ) -> MessageEnvelope:
        envelope = create_message(
            message_type,
            payload,
            correlation_id=correlation_id,
            headers=headers,
        )
        await self._bus.publish(envelope, messaging_route(message_type))
        return envelope

    async def _subscribe_events(self) -> None:
        await self._bus.subscribe(
            self.events_queue,
            [ROUTING_KEY_ALL_EVENTS],
            self._on_event_envelope,
        )

    async def _on_event_envelope(self, envelope: MessageEnvelope) -> None:
        self._logger.info(
            "event_received",
            message_type=envelope.type,
            correlation_id=str(envelope.correlation_id) if envelope.correlation_id else None,
        )
        for handler in self._event_handlers:
            await handler(envelope)