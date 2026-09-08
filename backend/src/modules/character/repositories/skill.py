from src.repositories.sql_alchemy import SQLAlchemyRepository
from src.modules.character.models import Skill

class SkillRepository(SQLAlchemyRepository):
    model = Skill