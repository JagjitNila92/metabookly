"""
Admin endpoints — feature flags, plan management, account overrides.

All routes require the 'admins' Cognito group.

Endpoints
─────────
GET    /admin/flags/global                           List all global feature flags
PATCH  /admin/flags/global/{flag_name}               Toggle a global flag
GET    /admin/flags/{account_type}/{account_id}      List per-account flag overrides
PATCH  /admin/flags/{account_type}/{account_id}/{flag_name}   Set override
DELETE /admin/flags/{account_type}/{account_id}/{flag_name}   Remove override (fall back to global)

PATCH  /admin/retailers/{retailer_id}/plan           Change a retailer's plan tier
"""
import uuid
from datetime import datetime, UTC

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_db, require_admin
from app.auth.models import CurrentUser
from app.models.feature_flags import GlobalFeatureFlag, AccountFeatureFlag
from app.models.retailer import Retailer
from app.services.feature_flag_service import FeatureFlagService

router = APIRouter(prefix="/admin", tags=["admin"])

VALID_ACCOUNT_TYPES = {"retailer", "publisher", "distributor"}
VALID_PLANS = {"free", "starter_api", "intelligence", "enterprise"}


# ── Schemas ───────────────────────────────────────────────────────────────────

class GlobalFlagOut(BaseModel):
    flag_name: str
    enabled: bool
    description: str | None
    updated_at: datetime
    updated_by: str | None

    model_config = {"from_attributes": True}


class GlobalFlagPatch(BaseModel):
    enabled: bool


class AccountFlagOut(BaseModel):
    id: uuid.UUID
    account_type: str
    account_id: uuid.UUID
    flag_name: str
    enabled: bool
    updated_at: datetime
    updated_by: str | None

    model_config = {"from_attributes": True}


class AccountFlagPatch(BaseModel):
    enabled: bool


class RetailerPlanPatch(BaseModel):
    plan: str
    extra_seats: int = 0


class RetailerPlanOut(BaseModel):
    id: uuid.UUID
    company_name: str
    email: str
    plan: str
    extra_seats: int
    plan_activated_at: datetime | None
    plan_expires_at: datetime | None

    model_config = {"from_attributes": True}


# ── Public flag read (no auth) ────────────────────────────────────────────────

class PublicFlagOut(BaseModel):
    flag_name: str
    enabled: bool


@router.get("/flags/public", response_model=list[PublicFlagOut])
async def list_public_flags(
    db: AsyncSession = Depends(get_db),
) -> list[PublicFlagOut]:
    """
    Public read of all global feature flags — returns name + enabled only.
    No auth required. Used by the frontend to gate UI elements.
    """
    svc = FeatureFlagService(db)
    flags = await svc.get_all_global()
    return [PublicFlagOut(flag_name=f.flag_name, enabled=f.enabled) for f in flags]


# ── Global flags (admin) ──────────────────────────────────────────────────────

@router.get("/flags/global", response_model=list[GlobalFlagOut])
async def list_global_flags(
    db: AsyncSession = Depends(get_db),
    _: CurrentUser = Depends(require_admin),
) -> list[GlobalFlagOut]:
    """List all global feature flags with full admin metadata."""
    svc = FeatureFlagService(db)
    flags = await svc.get_all_global()
    return [GlobalFlagOut.model_validate(f) for f in flags]


@router.patch("/flags/global/{flag_name}", response_model=GlobalFlagOut)
async def set_global_flag(
    flag_name: str,
    body: GlobalFlagPatch,
    db: AsyncSession = Depends(get_db),
    current_user: CurrentUser = Depends(require_admin),
) -> GlobalFlagOut:
    """Toggle a global feature flag. Creates the flag if it doesn't exist."""
    svc = FeatureFlagService(db)
    flag = await svc.set_global(flag_name, body.enabled, updated_by=current_user.sub)
    await db.commit()
    await db.refresh(flag)
    return GlobalFlagOut.model_validate(flag)


# ── Per-account overrides ─────────────────────────────────────────────────────

@router.get(
    "/flags/{account_type}/{account_id}",
    response_model=list[AccountFlagOut],
)
async def list_account_flags(
    account_type: str,
    account_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    _: CurrentUser = Depends(require_admin),
) -> list[AccountFlagOut]:
    """List all per-account flag overrides for a specific account."""
    if account_type not in VALID_ACCOUNT_TYPES:
        raise HTTPException(400, f"account_type must be one of: {', '.join(VALID_ACCOUNT_TYPES)}")
    svc = FeatureFlagService(db)
    overrides = await svc.get_account_overrides(account_type, account_id)
    return [AccountFlagOut.model_validate(o) for o in overrides]


@router.patch(
    "/flags/{account_type}/{account_id}/{flag_name}",
    response_model=AccountFlagOut,
)
async def set_account_flag(
    account_type: str,
    account_id: uuid.UUID,
    flag_name: str,
    body: AccountFlagPatch,
    db: AsyncSession = Depends(get_db),
    current_user: CurrentUser = Depends(require_admin),
) -> AccountFlagOut:
    """Set or update a per-account feature flag override."""
    if account_type not in VALID_ACCOUNT_TYPES:
        raise HTTPException(400, f"account_type must be one of: {', '.join(VALID_ACCOUNT_TYPES)}")
    svc = FeatureFlagService(db)
    override = await svc.set_account_override(
        account_type, account_id, flag_name, body.enabled, updated_by=current_user.sub
    )
    await db.commit()
    return AccountFlagOut.model_validate(override)


@router.delete(
    "/flags/{account_type}/{account_id}/{flag_name}",
    status_code=204,
)
async def delete_account_flag(
    account_type: str,
    account_id: uuid.UUID,
    flag_name: str,
    db: AsyncSession = Depends(get_db),
    _: CurrentUser = Depends(require_admin),
) -> None:
    """Remove a per-account override so the account falls back to the global flag value."""
    if account_type not in VALID_ACCOUNT_TYPES:
        raise HTTPException(400, f"account_type must be one of: {', '.join(VALID_ACCOUNT_TYPES)}")
    svc = FeatureFlagService(db)
    deleted = await svc.delete_account_override(account_type, account_id, flag_name)
    if not deleted:
        raise HTTPException(404, "Override not found")
    await db.commit()


# ── Retailer plan management ──────────────────────────────────────────────────

@router.patch("/retailers/{retailer_id}/plan", response_model=RetailerPlanOut)
async def set_retailer_plan(
    retailer_id: uuid.UUID,
    body: RetailerPlanPatch,
    db: AsyncSession = Depends(get_db),
    current_user: CurrentUser = Depends(require_admin),
) -> RetailerPlanOut:
    """Change a retailer's plan tier. Records activation timestamp on upgrade."""
    if body.plan not in VALID_PLANS:
        raise HTTPException(400, f"plan must be one of: {', '.join(VALID_PLANS)}")

    retailer = (
        await db.execute(select(Retailer).where(Retailer.id == retailer_id))
    ).scalar_one_or_none()
    if retailer is None:
        raise HTTPException(404, "Retailer not found")

    now = datetime.now(UTC).replace(tzinfo=None)
    upgrading = body.plan != "free" and retailer.plan == "free"
    retailer.plan = body.plan
    retailer.extra_seats = body.extra_seats
    if upgrading or (body.plan != "free" and retailer.plan_activated_at is None):
        retailer.plan_activated_at = now

    await db.commit()
    await db.refresh(retailer)
    return RetailerPlanOut.model_validate(retailer)
