import logging
from sqlalchemy.ext.asyncio import AsyncEngine, AsyncSession, async_sessionmaker, create_async_engine

logger = logging.getLogger(__name__)

_engine: AsyncEngine | None = None
_session_factory: async_sessionmaker[AsyncSession] | None = None


def create_engine(database_url: str, pool_size: int = 5, max_overflow: int = 10) -> AsyncEngine:
    return create_async_engine(
        database_url,
        pool_size=pool_size,
        max_overflow=max_overflow,
        pool_pre_ping=True,       # detects stale connections (important after Aurora cold start)
        pool_recycle=3600,        # recycle connections every hour
        echo=False,
    )


def init_engine(database_url: str, pool_size: int = 5, max_overflow: int = 10) -> None:
    global _engine, _session_factory
    _engine = create_engine(database_url, pool_size=pool_size, max_overflow=max_overflow)
    _session_factory = async_sessionmaker(_engine, expire_on_commit=False)
    logger.info("Database engine initialised")


def get_engine() -> AsyncEngine:
    if _engine is None:
        raise RuntimeError("Database engine not initialised — call init_engine() first")
    return _engine


def get_session_factory() -> async_sessionmaker[AsyncSession]:
    if _session_factory is None:
        raise RuntimeError("Session factory not initialised — call init_engine() first")
    return _session_factory


async def close_engine() -> None:
    global _engine, _session_factory
    if _engine:
        await _engine.dispose()
        _engine = None
        _session_factory = None
        logger.info("Database engine closed")
