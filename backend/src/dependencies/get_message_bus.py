from src.config import settings
from src.infrastructure.rabbitmq.bus import RabbitMQMessageBus
from src.infrastructure.rabbitmq.connection import RabbitMQConnection
from src.infrastructure.rabbitmq.topology import Topology
from src.messaging.interfaces import MessageBus


def get_message_bus() -> MessageBus:
    return RabbitMQMessageBus(
        connection=RabbitMQConnection(
            url=settings.RABBITMQ_URL,
            reconnect_interval_seconds=settings.RABBITMQ_RECONNECT_INTERVAL_SECONDS,
        ),
        topology=Topology(
            exchange_name=settings.RABBITMQ_EXCHANGE,
            queue_prefix=settings.RABBITMQ_QUEUE_PREFIX,
            exchange_type=settings.RABBITMQ_EXCHANGE_TYPE,
            retry_delay_seconds=settings.RABBITMQ_RETRY_DELAY_SECONDS,
        ),
        prefetch_count=settings.RABBITMQ_PREFETCH_COUNT,
        max_retries=settings.RABBITMQ_MAX_RETRIES,
    )
