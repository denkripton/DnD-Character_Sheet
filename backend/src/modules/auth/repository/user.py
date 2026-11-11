from src.modules.auth.models import User
from src.repositories.sql_alchemy import SQLAlchemyRepository


class UserRepository(SQLAlchemyRepository):
    model = User

    async def get_by_email(self, email: str):
        user = await self.get_one(email=email)
        return user
