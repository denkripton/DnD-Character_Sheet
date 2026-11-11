from pydantic import model_validator
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
