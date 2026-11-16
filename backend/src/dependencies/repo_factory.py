from fastapi import Depends
from sqlalchemy.ext.asyncio import AsyncSession

from src.dependencies.get_session import get_session


class RepoFactory:
    def __init__(self, repo):
        self.repository_class = repo

    def __call__(self, session: AsyncSession = Depends(get_session)):
        return self.repository_class(session)
