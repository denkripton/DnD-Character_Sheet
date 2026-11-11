from typing import Optional

from pydantic import Field, model_validator
from src.modules.character.stats.schemas.background_increase import (
    BackgroundIncreaseSchema,
)
from src.modules.character.utils.enums.stats import Stats
from src.utils.schemas.base_schema import BaseSchema


class StatsCreateSchema(BaseSchema):
    strength: int = Field(ge=8, le=15, default=8)
    dexterity: int = Field(ge=8, le=15, default=8)
    constitution: int = Field(ge=8, le=15, default=8)
    intelligence: int = Field(ge=8, le=15, default=8)
    wisdom: int = Field(ge=8, le=15, default=8)
    charisma: int = Field(ge=8, le=15, default=8)
    background_increase: Optional[BackgroundIncreaseSchema] = None

    @model_validator(mode="after")
    def validate_point_buy(self):
        stats = [
            ("strength", self.strength),
            ("dexterity", self.dexterity),
            ("constitution", self.constitution),
            ("intelligence", self.intelligence),
            ("wisdom", self.wisdom),
            ("charisma", self.charisma),
        ]

        costs_dict = Stats.STATS_COST.value
        total_cost = 0

        for key, stat in stats:
            if stat not in costs_dict:
                raise ValueError(f"Stat {key} is out of Point Buy range.")

            total_cost += costs_dict[stat]

        max_points = Stats.STATS_POINTS.value
        if total_cost != max_points:
            raise ValueError(
                f"You must spend exactly {max_points} points! Spent: {total_cost}/{max_points}."
            )

        if self.background_increase is not None:
            for key, increment in self.background_increase.increases.items():
                base_value = getattr(self, key)
                if base_value + increment > 20:
                    raise ValueError(
                        f"No ability score may exceed 20: {key} would reach "
                        f"{base_value + increment}."
                    )

        return self
