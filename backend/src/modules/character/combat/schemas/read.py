import uuid

from src.modules.character.combat.schemas.create import CombatCreateSchema


class CombatReadSchema(CombatCreateSchema):
    id: uuid.UUID