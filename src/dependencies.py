from typing import Callable

from sqlalchemy.ext.asyncio import AsyncSession
from fastapi import Depends, HTTPException

from src.exceptions import ServiceError
from src.config import logger
from src.databases import AsyncSessionLocal


async def get_session() -> AsyncSession:
    async with AsyncSessionLocal() as session:
        try:
            yield session
        finally:
            await session.close()


async def get_error(method: Callable, *args, **kwargs):
    try:
        return await method(*args, **kwargs)
    except ServiceError as service_e:
        raise HTTPException(status_code=service_e.status_code, detail=service_e.message)
    except Exception as e:
        logger.critical(e)


class RepoFactory:
    def __init__(self, repo):
        self.repository_class = repo

    def __call__(self, session: AsyncSession = Depends(get_session)):
        return self.repository_class(session)
