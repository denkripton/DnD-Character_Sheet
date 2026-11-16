from fastapi import Depends
from sqlalchemy.ext.asyncio import AsyncSession

from src.databases import UnitOfWork
from src.dependencies.get_session import get_session


async def get_unit_of_work(
    session: AsyncSession = Depends(get_session),
) -> UnitOfWork:
    uow = UnitOfWork(session=session)
    try:
        yield uow
    except Exception:
        await uow.rollback()
        raise
