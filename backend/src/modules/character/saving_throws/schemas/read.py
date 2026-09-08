import uuid

from src.utils.schemas.base_schema import BaseSchema


class SavingThrowsCreateSchema(BaseSchema):
    strength: bool = False
    dexterity: bool = False
    constitution: bool = False
    intelligence: bool = False
    wisdom: bool = False
    charisma: bool = False


class SavingThrowsReadSchema(SavingThrowsCreateSchema):
    id: uuid.UUID