from pydantic import Field, model_validator
from src.modules.character.utils.enums.stats import Stats
from src.utils.schemas.base_schema import BaseSchema


class StatsCreateSchema(BaseSchema):
    strength: int = Field(ge=8, le=17, default=8)
    dexterity: int = Field(ge=8, le=17, default=8)
    constitution: int = Field(ge=8, le=17, default=8)
    intelligence: int = Field(ge=8, le=17, default=8)
    wisdom: int = Field(ge=8, le=17, default=8)
    charisma: int = Field(ge=8, le=17, default=8)

    @model_validator(mode="after")
    def validate_point_buy(self):
        stats = [
            self.strength, self.dexterity, self.constitution,
            self.intelligence, self.wisdom, self.charisma
        ]
        
        costs_dict = Stats.STATS_COST.value
        total_cost = 0
        
        for stat in stats:
            if stat not in costs_dict:
                raise ValueError(f"Stat {stat} is out of Point Buy range.")
            
            total_cost += costs_dict[stat]
            
        max_points = Stats.STATS_POINTS.value
        if total_cost != max_points:
            raise ValueError(f"You must spend exactly {max_points} points! Spent: {total_cost}/{max_points}.")
            
        return self
