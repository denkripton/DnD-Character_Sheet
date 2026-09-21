from enum import Enum


class MessageType(str, Enum):
    CHARACTER_CREATE = "character.create.command"
    CHARACTER_UPDATE = "character.update.command"
    CHARACTER_GET = "character.get.command"
    CHARACTER_GENERATE = "character.generate.command"
    CHARACTER_GENERATE_BACKSTORY = "character.generate_backstory.command"
    CHARACTER_UPDATE_PARAMETER = "character.update_parameter.command"
    CHARACTER_DELETE = "character.delete.command"

    CHARACTER_CREATED = "character.created.event"
    CHARACTER_UPDATED = "character.updated.event"
    CHARACTER_GENERATED = "character.generated.event"
    CHARACTER_DELETED = "character.deleted.event"