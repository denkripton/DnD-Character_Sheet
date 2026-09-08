from src.repositories.sql_alchemy import SQLAlchemyRepository
from src.modules.character.models import Proficiency

class ProficiencyRepository(SQLAlchemyRepository):
    model = Proficiency