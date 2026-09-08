import uuid

from src.modules.character.skills.schemas.create import SkillCreateSchema


class SkillReadSchema(SkillCreateSchema):
    id: uuid.UUID