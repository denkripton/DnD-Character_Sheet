from src.messaging.enums.constants.message_content_type import MessageContentType
from src.messaging.enums.constants.message_header import MessageHeader
from src.messaging.enums.constants.messaging_queue import MessagingQueue
from src.messaging.enums.constants.messaging_routing_key import MessagingRoutingKey
from src.messaging.enums.constants.rabbitmq_argument import RabbitMQArgument
from src.messaging.enums.constants.topology_suffix import TopologySuffix

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
