from typing import Optional

from pydantic import Field

from src.utils.schemas.base_schema import BaseSchema


class CombatCreateSchema(BaseSchema):
    current_hp: Optional[int] = Field(default=None, ge=0, le=99999)
    max_hp: Optional[int] = Field(default=None, ge=0, le=99999)
    temp_hp: int = Field(ge=0, le=99999, default=0)
    bonus_hp: int = Field(default=0, ge=0, le=99999)
    armor_class: int = Field(ge=0, le=255)
    initiative: int = Field(ge=-50, le=50, default=0)
    speed: int = Field(ge=0, le=10000, default=30)
    proficiency_bonus: Optional[int] = Field(default=None, ge=0, le=20)
    hit_dice_total: Optional[str] = Field(default=None, max_length=20, examples=["1d10"])
    hit_dice_remaining: Optional[int] = Field(default=None, ge=0, le=100)
    inspiration: bool = False
    death_save_successes: int = Field(ge=0, le=3, default=0)
    death_save_failures: int = Field(ge=0, le=3, default=0)