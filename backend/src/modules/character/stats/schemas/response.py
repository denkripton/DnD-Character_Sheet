from src.modules.character.stats.schemas.read import StatsReadSchema
from src.modules.character.stats.schemas.read_modifiers import ModifiersReadSchema
from src.utils.schemas.base_schema import BaseSchema


class StatsResponseSchema(BaseSchema):
    stats: StatsReadSchema | None
    modifiers: ModifiersReadSchema | None