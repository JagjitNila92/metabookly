"""
Seed a demo retailer in the database for local development.

Creates:
  - A Retailer record (linked to the demo Cognito user by sub)
  - A RetailerDistributor record pointing to the MOCK connector

The Cognito user must exist first. Create it with:
  aws cognito-idp admin-create-user \
    --user-pool-id eu-west-2_Hb5mR6Ugo \
    --username demo@metabookly.com \
    --temporary-password 'Metabookly1!' \
    --message-action SUPPRESS

Then set a permanent password:
  aws cognito-idp admin-set-user-password \
    --user-pool-id eu-west-2_Hb5mR6Ugo \
    --username demo@metabookly.com \
    --password 'Metabookly1!' \
    --permanent

Usage:
  python scripts/seed_demo_retailer.py <cognito_sub>
"""
import asyncio
import sys
import os

# Fallback sub if not provided — will need replacing with real value
DEFAULT_SUB = os.getenv("DEMO_COGNITO_SUB", "REPLACE_WITH_COGNITO_SUB")

async def seed():
    os.environ.setdefault(
        "DATABASE_URL",
        "postgresql+asyncpg://metabookly:metabookly_dev@localhost:5432/metabookly",
    )

    from sqlalchemy import select, text
    from sqlalchemy.dialects.postgresql import insert as pg_insert
    from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
    from sqlalchemy.orm import sessionmaker

    cognito_sub = sys.argv[1] if len(sys.argv) > 1 else DEFAULT_SUB

    engine = create_async_engine(os.environ["DATABASE_URL"])
    async_session = sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)

    async with async_session() as session:
        from app.models.retailer import Retailer, RetailerDistributor

        # Upsert retailer
        stmt = (
            pg_insert(Retailer)
            .values(
                cognito_sub=cognito_sub,
                company_name="Demo Bookshop",
                email="demo@metabookly.com",
                country_code="GB",
                active=True,
            )
            .on_conflict_do_update(
                index_elements=["cognito_sub"],
                set_={"company_name": "Demo Bookshop", "active": True},
            )
            .returning(Retailer.id)
        )
        result = await session.execute(stmt)
        retailer_id = result.scalar_one()
        print(f"Retailer upserted: {retailer_id}")

        # Upsert MOCK distributor account
        stmt2 = (
            pg_insert(RetailerDistributor)
            .values(
                retailer_id=retailer_id,
                distributor_code="MOCK",
                account_number="DEMO-001",
                active=True,
            )
            .on_conflict_do_nothing()
        )
        await session.execute(stmt2)
        print("MOCK distributor account linked")

        await session.commit()

    await engine.dispose()
    print("Done. Demo retailer is ready.")


if __name__ == "__main__":
    asyncio.run(seed())
