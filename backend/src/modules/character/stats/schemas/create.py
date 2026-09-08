from typing import Optional

from pydantic import Field, model_validator

from src.modules.character.utils.enums.stats import Stats
from src.modules.character.utils.hit_points import ABILITY_NAMES
from src.utils.schemas.base_schema import BaseSchema


class BackgroundIncreaseSchema(BaseSchema):
    increases: dict[str, int]

    @model_validator(mode="after")
    def validate_increases(self):
        if not self.increases:
            raise ValueError("Background increase is required")

        for key, value in self.increases.items():
            if key not in ABILITY_NAMES:
                raise ValueError(f"Unknown ability score: {key}")
            if value not in (1, 2):
                raise ValueError(
                    f"Background increase for {key} must be 1 or 2, got {value}"
                )

        values = list(self.increases.values())
        if len(values) == 3 and values.count(1) == 3:
            return self

        if (
            len(values) == 2
            and values.count(2) == 1
            and values.count(1) == 1
        ):
            return self

        raise ValueError(
            "Background must increase one ability by 2 and another by 1, "
            "or three abilities by 1 each"
        )


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