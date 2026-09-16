from fastapi import Depends
from sqlalchemy.ext.asyncio import AsyncSession

from src.databases.sql import AsyncSessionLocal
from src.utils.unit_of_work import UnitOfWork


async def get_session() -> AsyncSession:
    async with AsyncSessionLocal() as session:
        try:
            yield session
        finally:
            await session.close()


async def get_unit_of_work(
    session: AsyncSession = Depends(get_session),
) -> UnitOfWork:
    uow = UnitOfWork(session=session)
    try:
        yield uow
    except Exception:
        await uow.rollback()
        raise


class RepoFactory:
    def __init__(self, repo):
        self.repository_class = repo

    def __call__(self, session: AsyncSession = Depends(get_session)):
        return self.repository_class(session)
