from src.modules.character.models import CharacterDraft
from src.repositories.sql_alchemy import SQLAlchemyRepository


class CharacterDraftRepository(SQLAlchemyRepository):
    model = CharacterDraft
