from aio_pika import DeliveryMode, ExchangeType, Message

from src.infrastructure.rabbitmq.connection import RabbitMQConnection
from src.infrastructure.rabbitmq.serialization import serialize
from src.infrastructure.rabbitmq.topology import Topology
from src.infrastructure.rabbitmq.utils import envelope_to_properties
from src.messaging.constants import CONTENT_TYPE_JSON
from src.messaging.interfaces import MessagePublisher
from src.messaging.messages import MessageEnvelope


class RabbitMQPublisher(MessagePublisher):
    def __init__(
        self,
        connection: RabbitMQConnection,
        topology: Topology,
    ):
        self._connection = connection
        self._topology = topology

    async def publish(self, envelope: MessageEnvelope, routing_key: str) -> None:
        channel = await self._connection.channel()
        exchange = await channel.declare_exchange(
            name=self._topology.exchange_name,
            type=ExchangeType(self._topology.exchange_type),
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
        await exchange.publish(message, routing_key, mandatory=True)