from src.repositories.sql_alchemy import SQLAlchemyRepository
from src.modules.character.models import Personality

class PersonalityRepository(SQLAlchemyRepository):
    model = Personality