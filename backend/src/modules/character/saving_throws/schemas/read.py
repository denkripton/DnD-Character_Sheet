import uuid

from src.modules.character.saving_throws.schemas.create import SavingThrowsCreateSchema


class SavingThrowsReadSchema(SavingThrowsCreateSchema):
    id: uuid.UUID
