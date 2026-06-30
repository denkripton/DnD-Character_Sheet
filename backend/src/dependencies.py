from fastapi import Depends
from sqlalchemy.ext.asyncio import AsyncSession

from src.databases.sql import AsyncSessionLocal


async def get_session() -> AsyncSession:
    async with AsyncSessionLocal() as session:
        try:
            yield session
        finally:
            await session.close()


class RepoFactory:
    def __init__(self, repo):
        self.repository_class = repo

    def __call__(self, session: AsyncSession = Depends(get_session)):
        return self.repository_class(session)
