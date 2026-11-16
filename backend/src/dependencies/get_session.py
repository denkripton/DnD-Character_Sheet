from sqlalchemy.ext.asyncio import AsyncSession

from src.databases.sql import AsyncSessionLocal


async def get_session() -> AsyncSession:
    async with AsyncSessionLocal() as session:
        try:
            yield session
        finally:
            await session.close()
