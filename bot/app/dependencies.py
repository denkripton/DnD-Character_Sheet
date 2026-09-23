from app.config import BotConfig
from app.infrastructure.rabbitmq.client import BotRabbitMQClient


def build_rabbitmq_client(config: BotConfig) -> BotRabbitMQClient:
    return BotRabbitMQClient(config=config)