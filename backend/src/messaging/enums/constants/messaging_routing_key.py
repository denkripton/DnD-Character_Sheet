from enum import StrEnum


class MessagingRoutingKey(StrEnum):
    ALL_COMMANDS = "commands.#"
    ALL_EVENTS = "events.#"
