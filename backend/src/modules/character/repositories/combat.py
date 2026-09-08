from src.repositories.sql_alchemy import SQLAlchemyRepository
from src.modules.character.models import Combat

class CombatRepository(SQLAlchemyRepository):
    model = Combat