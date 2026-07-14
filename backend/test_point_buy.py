from pydantic import ValidationError
from src.modules.character.schemas.stats.create import StatsCreateSchema

try:
    schema = StatsCreateSchema(strength=8, dexterity=8, constitution=8, intelligence=8, wisdom=8, charisma=8)
    print("Success:", schema)
except ValidationError as e:
    print("Error:", e)
