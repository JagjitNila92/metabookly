"""
Feature flag resolution service.

Resolution order (highest wins):
  1. Per-account override (account_feature_flags)
  2. Global flag (global_feature_flags)
  3. Hard-coded default: False

Usage:
    svc = FeatureFlagService(db)
    await svc.is_enabled("ordering_enabled")
    await svc.is_enabled("ordering_enabled", account_type="retailer", account_id=retailer.id)
"""
import uuid
from datetime import datetime, UTC

from sqlalchemy import select
from sqlalchemy.dialects.postgresql import insert as pg_insert
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.feature_flags import AccountFeatureFlag, GlobalFeatureFlag


class FeatureFlagService:
    def __init__(self, db: AsyncSession) -> None:
        self._db = db

    async def is_enabled(
        self,
        flag_name: str,
        account_type: str | None = None,
        account_id: uuid.UUID | None = None,
    ) -> bool:
        """
        Resolve a feature flag for an optional account context.

        If account_type + account_id are given, check for a per-account override
        first. If no override exists, fall back to the global flag value.
        """
        if account_type and account_id:
            override = (
                await self._db.execute(
                    select(AccountFeatureFlag).where(
                        AccountFeatureFlag.account_type == account_type,
                        AccountFeatureFlag.account_id == account_id,
                        AccountFeatureFlag.flag_name == flag_name,
                    )
                )
            ).scalar_one_or_none()
            if override is not None:
                return override.enabled

        global_flag = (
            await self._db.execute(
                select(GlobalFeatureFlag).where(GlobalFeatureFlag.flag_name == flag_name)
            )
        ).scalar_one_or_none()

        return global_flag.enabled if global_flag is not None else False

    async def get_all_global(self) -> list[GlobalFeatureFlag]:
        result = await self._db.execute(
            select(GlobalFeatureFlag).order_by(GlobalFeatureFlag.flag_name)
        )
        return list(result.scalars().all())

    async def set_global(
        self, flag_name: str, enabled: bool, updated_by: str
    ) -> GlobalFeatureFlag:
        flag = (
            await self._db.execute(
                select(GlobalFeatureFlag).where(GlobalFeatureFlag.flag_name == flag_name)
            )
        ).scalar_one_or_none()

        if flag is None:
            flag = GlobalFeatureFlag(
                flag_name=flag_name,
                enabled=enabled,
                updated_by=updated_by,
            )
            self._db.add(flag)
        else:
            flag.enabled = enabled
            flag.updated_by = updated_by
            flag.updated_at = datetime.now(UTC).replace(tzinfo=None)

        await self._db.flush()
        return flag

    async def get_account_overrides(
        self, account_type: str, account_id: uuid.UUID
    ) -> list[AccountFeatureFlag]:
        result = await self._db.execute(
            select(AccountFeatureFlag).where(
                AccountFeatureFlag.account_type == account_type,
                AccountFeatureFlag.account_id == account_id,
            ).order_by(AccountFeatureFlag.flag_name)
        )
        return list(result.scalars().all())

    async def set_account_override(
        self,
        account_type: str,
        account_id: uuid.UUID,
        flag_name: str,
        enabled: bool,
        updated_by: str,
    ) -> AccountFeatureFlag:
        now = datetime.now(UTC).replace(tzinfo=None)
        stmt = (
            pg_insert(AccountFeatureFlag)
            .values(
                id=uuid.uuid4(),
                account_type=account_type,
                account_id=account_id,
                flag_name=flag_name,
                enabled=enabled,
                updated_by=updated_by,
                updated_at=now,
            )
            .on_conflict_do_update(
                constraint="uq_account_feature_flags",
                set_={"enabled": enabled, "updated_by": updated_by, "updated_at": now},
            )
            .returning(AccountFeatureFlag)
        )
        result = await self._db.execute(stmt)
        await self._db.flush()
        return result.scalar_one()

    async def delete_account_override(
        self, account_type: str, account_id: uuid.UUID, flag_name: str
    ) -> bool:
        """Remove a per-account override so it falls back to the global value. Returns True if deleted."""
        override = (
            await self._db.execute(
                select(AccountFeatureFlag).where(
                    AccountFeatureFlag.account_type == account_type,
                    AccountFeatureFlag.account_id == account_id,
                    AccountFeatureFlag.flag_name == flag_name,
                )
            )
        ).scalar_one_or_none()

        if override is None:
            return False
        await self._db.delete(override)
        await self._db.flush()
        return True
