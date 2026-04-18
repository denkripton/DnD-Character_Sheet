from src.repositories.sql_alchemy import SQLAlchemyRepository
from src.modules.character.models.character import Character

class CharacterRepository(SQLAlchemyRepository):
    model = Character