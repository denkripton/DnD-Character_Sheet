from src.repositories.sql_alchemy import SQLAlchemyRepository
from src.modules.character.models import Backstory


class BackstoryRepository(SQLAlchemyRepository):
    model = Backstory