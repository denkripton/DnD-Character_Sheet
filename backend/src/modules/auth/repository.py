from src.modules.auth.models import ExternalIdentity, User
from src.repositories.sql_alchemy import SQLAlchemyRepository


class UserRepository(SQLAlchemyRepository):
    model = User

    async def get_by_email(self, email: str):
        user = await self.get_one(email=email)
        return user


class ExternalIdentityRepository(SQLAlchemyRepository):
    model = ExternalIdentity

    async def get_by_provider(self, provider: str, provider_user_id: str):
        identity = await self.get_one(
            provider=provider, provider_user_id=provider_user_id
        )
        return identity