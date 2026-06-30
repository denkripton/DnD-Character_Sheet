from src.repositories.sql_alchemy import SQLAlchemyRepository
from src.modules.auth.models import User


class UserRepository(SQLAlchemyRepository):
    model = User

    async def get_by_email(self, email: str):
        user = await self.get_one(email=email)
        return user