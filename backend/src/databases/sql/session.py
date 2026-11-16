from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from src.databases.sql.engine import engine

AsyncSessionLocal = async_sessionmaker(
    bind=engine, expire_on_commit=False, class_=AsyncSession, autoflush=False
)
