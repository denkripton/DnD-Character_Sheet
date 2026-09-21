from aio_pika import DeliveryMode, ExchangeType, Message
from pamqp.commands import Basic

from src.infrastructure.rabbitmq.connection import RabbitMQConnection
from src.infrastructure.rabbitmq.serialization import serialize
from src.infrastructure.rabbitmq.topology import Topology
from src.infrastructure.rabbitmq.utils import envelope_to_properties
from src.messaging.enums.constants import CONTENT_TYPE_JSON, RETRY_COUNT_HEADER
from src.messaging.interfaces import MessagePublisher
from src.messaging.messages import MessageEnvelope
from src.utils.exceptions import RabbitMQMessagePublishError


class RabbitMQPublisher(MessagePublisher):
    def __init__(
        self,
        connection: RabbitMQConnection,
        topology: Topology,
    ):
        self._connection = connection
        self._topology = topology

    async def publish(self, envelope: MessageEnvelope, routing_key: str) -> None:
        await self._publish(
            envelope,
            routing_key,
            self._topology.exchange_name,
            ExchangeType(self._topology.exchange_type),
        )

    async def publish_retry(
        self,
        envelope: MessageEnvelope,
        routing_key: str,
        retry_count: int,
    ) -> None:
        retry_envelope = envelope.model_copy(
            update={
                "headers": {
                    **envelope.headers,
                    RETRY_COUNT_HEADER: str(retry_count),
                }
            }
        )
        await self._publish(
            retry_envelope,
            routing_key,
            self._topology.retry_exchange_name,
            ExchangeType.DIRECT,
        )

    async def _publish(
        self,
        envelope: MessageEnvelope,
        routing_key: str,
        exchange_name: str,
        exchange_type: ExchangeType,
    ) -> None:
        async with self._connection.channel() as channel:
            exchange = await channel.declare_exchange(
                name=exchange_name,
                type=exchange_type,
                durable=True,
            )
            properties = envelope_to_properties(envelope)
            message = Message(
                body=serialize(envelope),
                content_type=CONTENT_TYPE_JSON,
                delivery_mode=DeliveryMode.PERSISTENT,
                message_id=properties.message_id,
                correlation_id=properties.correlation_id,
                timestamp=properties.timestamp,
                headers=properties.headers,
                type=properties.type,
            )
            confirmation = await exchange.publish(
                message,
                routing_key,
                mandatory=True,
            )
            if isinstance(confirmation, Basic.Nack):
                raise RabbitMQMessagePublishError(
                    f"Broker rejected message {envelope.message_id}"
                )