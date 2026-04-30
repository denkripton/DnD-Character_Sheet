from src.repositories.sql_alchemy import SQLAlchemyRepository
from src.modules.character.models import Stat

class StatsRepository(SQLAlchemyRepository):
    model = Stat