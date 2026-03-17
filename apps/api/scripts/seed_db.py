"""
Seed the local development database by ingesting the seed ONIX catalog.

Runs the full stack: ONIX parser → upsert service → PostgreSQL.
This tests the entire ingest pipeline end-to-end.

Usage:
    cd apps/api
    python scripts/seed_db.py
"""
import asyncio
import sys
from pathlib import Path

# Allow running from apps/api/ directly
sys.path.insert(0, str(Path(__file__).parent.parent))

from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine
from sqlalchemy.orm import sessionmaker

from app.config import get_settings
from app.services.onix_service import ingest_onix

FIXTURE = Path(__file__).parent.parent / "tests" / "fixtures" / "seed_catalog.xml"


async def main():
    settings = get_settings()
    engine = create_async_engine(settings.database_url, echo=False)
    async_session = sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)

    print(f"Seeding from: {FIXTURE}")
    print(f"Database:     {settings.database_url}\n")

    async with async_session() as session:
        result = await ingest_onix(
            session,
            FIXTURE,
            triggered_by="seed-script",
            s3_bucket="local-dev",
            s3_key="seed_catalog.xml",
        )
        await session.commit()

    print(f"Status:    {result['status']}")
    print(f"Found:     {result['records_found']} products")
    print(f"Upserted:  {result['records_upserted']} books")
    print(f"Failed:    {result['records_failed']}")
    if result["errors"]:
        print("\nErrors:")
        for e in result["errors"]:
            print(f"  {e}")

    await engine.dispose()
    return 0 if result["status"] != "failed" else 1


if __name__ == "__main__":
    sys.exit(asyncio.run(main()))
