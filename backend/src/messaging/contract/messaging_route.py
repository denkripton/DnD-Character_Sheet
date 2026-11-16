from src.messaging.enums import MessageType


def messaging_route(message_type: MessageType) -> str:
    parts = message_type.value.split(".")
    kind = parts[-1]
    namespace = "commands" if kind == "command" else "events"
    return f"{namespace}.{'.'.join(parts[:-1])}"
