from enum import StrEnum


class RabbitMQArgument(StrEnum):
    DEAD_LETTER_EXCHANGE = "x-dead-letter-exchange"
    MESSAGE_TTL = "x-message-ttl"
