from collections.abc import AsyncGenerator
from sqlalchemy.ext.asyncio import AsyncSession
from app.db.engine import get_session_factory


async def get_db() -> AsyncGenerator[AsyncSession, None]:
    """FastAPI dependency that provides a database session per request."""
    async with get_session_factory()() as session:
        try:
            yield session
            await session.commit()
        except Exception:
            await session.rollback()
            raise
