import uuid

from src.modules.character.proficiencies.schemas.create import ProficiencyCreateSchema


class ProficiencyReadSchema(ProficiencyCreateSchema):
    id: uuid.UUID