"""
Pytest configuration and shared fixtures.

DB isolation strategy: each test runs inside a transaction that is rolled back
on teardown, so tests are fully isolated without needing to truncate tables.

Local dev:  uses DATABASE_URL from .env by default
CI:         set TEST_DATABASE_URL=postgresql+asyncpg://metabookly:metabookly@localhost:5432/metabookly_test
"""
import os

import pytest
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine

# Fall back to the dev DB if no test-specific URL is provided.
# CI sets this to point at the dedicated metabookly_test database.
_TEST_DB_URL = os.getenv(
    "TEST_DATABASE_URL",
    "postgresql+asyncpg://metabookly:metabookly_dev@localhost:5432/metabookly",
)


@pytest.fixture
async def engine():
    eng = create_async_engine(_TEST_DB_URL, echo=False)
    yield eng
    await eng.dispose()


@pytest.fixture
async def session(engine):
    """
    Yields an AsyncSession whose work is rolled back after each test.

    The outer BEGIN + final rollback ensure nothing is committed to the DB,
    while join_transaction_mode='create_savepoint' lets the service code call
    session.flush() freely (each flush becomes a SAVEPOINT release internally).
    """
    async with engine.connect() as conn:
        await conn.begin()
        sess = AsyncSession(conn, join_transaction_mode="create_savepoint")
        yield sess
        await conn.rollback()
