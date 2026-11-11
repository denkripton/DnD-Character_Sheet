import uuid

from src.modules.character.personality.schemas.create import PersonalityCreateSchema


class PersonalityReadSchema(PersonalityCreateSchema):
    id: uuid.UUID
