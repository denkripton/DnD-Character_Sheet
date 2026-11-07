from sqlalchemy import select
from sqlalchemy.orm import selectinload

from src.modules.character.models import Character
from src.repositories.sql_alchemy import SQLAlchemyRepository


class CharacterRepository(SQLAlchemyRepository):
    model = Character

    async def get_with_sheet(self, character_id, owner_id):
        query = (
            select(self.model)
            .options(
                selectinload(Character.stats),
                selectinload(Character.combat),
                selectinload(Character.saving_throws),
                selectinload(Character.skills),
                selectinload(Character.proficiencies),
                selectinload(Character.features),
                selectinload(Character.personality),
                selectinload(Character.backstory),
            )
            .where(self.model.id == character_id, self.model.owner_id == owner_id)
        )
        result = await self.session.execute(query)
        return result.scalars().first()
