from src.repositories.sql_alchemy import SQLAlchemyRepository
from src.modules.character.models import SavingThrows

class SavingThrowsRepository(SQLAlchemyRepository):
    model = SavingThrows