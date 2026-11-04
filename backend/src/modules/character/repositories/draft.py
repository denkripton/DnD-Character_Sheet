from sqlalchemy import select
from src.modules.character.models import CharacterDraft
from src.repositories.sql_alchemy import SQLAlchemyRepository


class CharacterDraftRepository(SQLAlchemyRepository):
    model = CharacterDraft

    async def get_owned_for_update(self, draft_id, user_id):
        result = await self.session.execute(
            select(CharacterDraft)
            .where(CharacterDraft.id == draft_id, CharacterDraft.owner_id == user_id)
            .with_for_update()
        )
        return result.scalars().first()
