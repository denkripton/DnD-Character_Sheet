from src.repositories.sql_alchemy import SQLAlchemyRepository
from src.modules.character.models import Feature

class FeatureRepository(SQLAlchemyRepository):
    model = Feature