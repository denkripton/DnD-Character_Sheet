from enum import Enum

from src.utils.schemas.base_schema import BaseSchema


class SkillAbility(Enum):
    strength = "strength"
    dexterity = "dexterity"
    constitution = "constitution"
    intelligence = "intelligence"
    wisdom = "wisdom"
    charisma = "charisma"