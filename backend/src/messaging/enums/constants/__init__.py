from enum import StrEnum


class MessageHeader(StrEnum):
    COMMAND_SIGNATURE = "x-command-signature"
    AUTH_PROVIDER = "x-auth-provider"
    AUTH_PROVIDER_USER_ID = "x-auth-provider-user-id"
    AUTH_USER_ID = "x-user-id"
    RETRY_COUNT = "x-retry-count"


class RabbitMQArgument(StrEnum):
    DEAD_LETTER_EXCHANGE = "x-dead-letter-exchange"
    MESSAGE_TTL = "x-message-ttl"


class TopologySuffix(StrEnum):
    RETRY_EXCHANGE = ".retryx"
    RETRY_QUEUE = ".retry"
    DEAD_LETTER_EXCHANGE = ".dlx"
    DEAD_LETTER_QUEUE = ".dlq"


class MessagingRoutingKey(StrEnum):
    ALL_COMMANDS = "commands.#"
    ALL_EVENTS = "events.#"


class MessagingQueue(StrEnum):
    BOT_COMMANDS = "bot_commands"


class MessageContentType(StrEnum):
    JSON = "application/json"


COMMAND_SIGNATURE_HEADER = MessageHeader.COMMAND_SIGNATURE.value
AUTH_PROVIDER_HEADER = MessageHeader.AUTH_PROVIDER.value
AUTH_PROVIDER_USER_ID_HEADER = MessageHeader.AUTH_PROVIDER_USER_ID.value
AUTH_USER_ID_HEADER = MessageHeader.AUTH_USER_ID.value
RETRY_COUNT_HEADER = MessageHeader.RETRY_COUNT.value
DEAD_LETTER_ARGUMENT = RabbitMQArgument.DEAD_LETTER_EXCHANGE.value
MESSAGE_TTL_ARGUMENT = RabbitMQArgument.MESSAGE_TTL.value
RETRY_EXCHANGE_SUFFIX = TopologySuffix.RETRY_EXCHANGE.value
RETRY_QUEUE_SUFFIX = TopologySuffix.RETRY_QUEUE.value
DEAD_LETTER_EXCHANGE_SUFFIX = TopologySuffix.DEAD_LETTER_EXCHANGE.value
DEAD_LETTER_QUEUE_SUFFIX = TopologySuffix.DEAD_LETTER_QUEUE.value
ROUTING_KEY_ALL_COMMANDS = MessagingRoutingKey.ALL_COMMANDS.value
ROUTING_KEY_ALL_EVENTS = MessagingRoutingKey.ALL_EVENTS.value
BOT_COMMAND_QUEUE = MessagingQueue.BOT_COMMANDS.value
CONTENT_TYPE_JSON = MessageContentType.JSON.value
EMPTY_HEADERS: dict[str, str] = {}

__all__ = [
    "AUTH_PROVIDER_HEADER",
    "AUTH_PROVIDER_USER_ID_HEADER",
    "AUTH_USER_ID_HEADER",
    "BOT_COMMAND_QUEUE",
    "COMMAND_SIGNATURE_HEADER",
    "CONTENT_TYPE_JSON",
    "DEAD_LETTER_ARGUMENT",
    "DEAD_LETTER_EXCHANGE_SUFFIX",
    "DEAD_LETTER_QUEUE_SUFFIX",
    "EMPTY_HEADERS",
    "MESSAGE_TTL_ARGUMENT",
    "RETRY_COUNT_HEADER",
    "RETRY_EXCHANGE_SUFFIX",
    "RETRY_QUEUE_SUFFIX",
    "ROUTING_KEY_ALL_COMMANDS",
    "ROUTING_KEY_ALL_EVENTS",
    "MessageContentType",
    "MessageHeader",
    "MessagingQueue",
    "MessagingRoutingKey",
    "RabbitMQArgument",
    "TopologySuffix",
]
