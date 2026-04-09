"""
Admin endpoints — feature flags, plan management, account overrides.

All routes require the 'admins' Cognito group.

Endpoints
─────────
GET    /admin/stats                                  Platform-wide stats
GET    /admin/retailers                              Paginated retailer list
GET    /admin/flags/global                           List all global feature flags
PATCH  /admin/flags/global/{flag_name}               Toggle a global flag
GET    /admin/flags/{account_type}/{account_id}      List per-account flag overrides
PATCH  /admin/flags/{account_type}/{account_id}/{flag_name}   Set override
DELETE /admin/flags/{account_type}/{account_id}/{flag_name}   Remove override (fall back to global)

PATCH  /admin/retailers/{retailer_id}/plan           Change a retailer's plan tier
"""
import logging
import secrets
import string
import uuid
from datetime import datetime, UTC, timedelta

import boto3
from botocore.exceptions import ClientError
from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel
from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_db, require_admin
from app.auth.models import CurrentUser
from app.config import get_settings
from app.models.feature_flags import GlobalFeatureFlag, AccountFeatureFlag
from app.models.retailer import Retailer
from app.models.ordering import Order
from app.models.book import Book
from app.models.portal import FeedSource
from app.services.feature_flag_service import FeatureFlagService
from app.services.email_service import send_publisher_invite_email

logger = logging.getLogger(__name__)


def _generate_temp_password() -> str:
    """Generate a 16-char random password meeting Cognito complexity requirements."""
    alphabet = string.ascii_letters + string.digits + "!@#$%^"
    while True:
        pwd = "".join(secrets.choice(alphabet) for _ in range(16))
        if (
            any(c.isupper() for c in pwd)
            and any(c.islower() for c in pwd)
            and any(c.isdigit() for c in pwd)
            and any(c in "!@#$%^" for c in pwd)
        ):
            return pwd

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


class RetailerListItem(BaseModel):
    id: uuid.UUID
    company_name: str
    email: str
    contact_name: str | None
    plan: str
    extra_seats: int
    active: bool
    created_at: datetime

    model_config = {"from_attributes": True}


class RetailerListOut(BaseModel):
    items: list[RetailerListItem]
    total: int
    page: int
    page_size: int


class PlanCounts(BaseModel):
    free: int
    starter_api: int
    intelligence: int
    enterprise: int


class PlatformStats(BaseModel):
    total_retailers: int
    retailers_by_plan: PlanCounts
    new_retailers_7d: int
    total_titles: int
    total_orders: int


# ── Platform stats ───────────────────────────────────────────────────────────

@router.get("/stats", response_model=PlatformStats)
async def get_platform_stats(
    db: AsyncSession = Depends(get_db),
    _: CurrentUser = Depends(require_admin),
) -> PlatformStats:
    """Platform-wide stats for the admin dashboard overview."""
    cutoff_7d = datetime.now(UTC).replace(tzinfo=None) - timedelta(days=7)

    # Retailer counts
    total_retailers = (await db.execute(select(func.count()).select_from(Retailer))).scalar_one()
    new_7d = (
        await db.execute(select(func.count()).select_from(Retailer).where(Retailer.created_at >= cutoff_7d))
    ).scalar_one()

    # Plan breakdown
    plan_rows = (
        await db.execute(
            select(Retailer.plan, func.count().label("n"))
            .group_by(Retailer.plan)
        )
    ).all()
    plan_map: dict[str, int] = {row.plan: row.n for row in plan_rows}

    # Catalog + orders
    total_titles = (await db.execute(select(func.count()).select_from(Book))).scalar_one()
    total_orders = (await db.execute(select(func.count()).select_from(Order))).scalar_one()

    return PlatformStats(
        total_retailers=total_retailers,
        retailers_by_plan=PlanCounts(
            free=plan_map.get("free", 0),
            starter_api=plan_map.get("starter_api", 0),
            intelligence=plan_map.get("intelligence", 0),
            enterprise=plan_map.get("enterprise", 0),
        ),
        new_retailers_7d=new_7d,
        total_titles=total_titles,
        total_orders=total_orders,
    )


# ── Retailer list ─────────────────────────────────────────────────────────────

@router.get("/retailers", response_model=RetailerListOut)
async def list_retailers(
    db: AsyncSession = Depends(get_db),
    _: CurrentUser = Depends(require_admin),
    page: int = Query(1, ge=1),
    page_size: int = Query(25, ge=1, le=100),
    search: str | None = Query(None),
    plan: str | None = Query(None),
) -> RetailerListOut:
    """Paginated, searchable list of all retailers."""
    stmt = select(Retailer).order_by(Retailer.created_at.desc())
    count_stmt = select(func.count()).select_from(Retailer)

    if search:
        like = f"%{search.lower()}%"
        stmt = stmt.where(
            func.lower(Retailer.company_name).like(like) | func.lower(Retailer.email).like(like)
        )
        count_stmt = count_stmt.where(
            func.lower(Retailer.company_name).like(like) | func.lower(Retailer.email).like(like)
        )

    if plan:
        stmt = stmt.where(Retailer.plan == plan)
        count_stmt = count_stmt.where(Retailer.plan == plan)

    total = (await db.execute(count_stmt)).scalar_one()
    offset = (page - 1) * page_size
    rows = (await db.execute(stmt.offset(offset).limit(page_size))).scalars().all()

    return RetailerListOut(
        items=[RetailerListItem.model_validate(r) for r in rows],
        total=total,
        page=page,
        page_size=page_size,
    )


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


# ── Publisher management ──────────────────────────────────────────────────────

class PublisherCreateRequest(BaseModel):
    company_name: str
    contact_email: str
    contact_name: str
    distributor_code: str | None = None
    source_type: str = "publisher"   # publisher | aggregator | distributor


class PublisherOut(BaseModel):
    id: uuid.UUID
    name: str
    contact_email: str | None
    source_type: str
    distributor_code: str | None
    managed_by: str
    active: bool
    created_at: datetime

    model_config = {"from_attributes": True}


class PublisherCreateOut(BaseModel):
    feed_source: PublisherOut
    temp_password: str     # shown once in the UI; also sent via email


@router.get("/publishers", response_model=list[PublisherOut])
async def list_publishers(
    db: AsyncSession = Depends(get_db),
    _: CurrentUser = Depends(require_admin),
) -> list[PublisherOut]:
    """List all publisher feed sources."""
    rows = (
        await db.execute(
            select(FeedSource)
            .where(FeedSource.source_type.in_(["publisher", "aggregator"]))
            .order_by(FeedSource.created_at.desc())
        )
    ).scalars().all()
    return [PublisherOut.model_validate(r) for r in rows]


@router.post("/publishers", response_model=PublisherCreateOut, status_code=201)
async def create_publisher(
    body: PublisherCreateRequest,
    db: AsyncSession = Depends(get_db),
    _: CurrentUser = Depends(require_admin),
) -> PublisherCreateOut:
    """
    Create a publisher portal account in one step:
    1. Cognito user created and added to 'publishers' group
    2. FeedSource row created and linked to their Cognito sub
    3. Welcome email sent with temporary password

    The temporary password is returned in this response (shown once) and emailed.
    """
    if body.source_type not in ("publisher", "aggregator", "distributor"):
        raise HTTPException(400, "source_type must be publisher | aggregator | distributor")

    settings = get_settings()
    cognito = boto3.client("cognito-idp", region_name=settings.aws_region)

    # 1. Check email not already used
    existing = (
        await db.execute(select(FeedSource).where(FeedSource.contact_email == body.contact_email))
    ).scalar_one_or_none()
    if existing:
        raise HTTPException(409, "A publisher account with this email already exists.")

    # 2. Create Cognito user
    temp_password = _generate_temp_password()
    try:
        resp = cognito.admin_create_user(
            UserPoolId=settings.cognito_user_pool_id,
            Username=body.contact_email,
            UserAttributes=[
                {"Name": "email", "Value": body.contact_email},
                {"Name": "email_verified", "Value": "true"},
                {"Name": "name", "Value": body.contact_name},
            ],
            MessageAction="SUPPRESS",
        )
        cognito_sub = next(
            a["Value"] for a in resp["User"]["Attributes"] if a["Name"] == "sub"
        )
    except ClientError as e:
        code = e.response["Error"]["Code"]
        if code == "UsernameExistsException":
            raise HTTPException(409, "A Cognito account with this email already exists.")
        logger.error("Cognito admin_create_user failed: %s", e)
        raise HTTPException(500, "Could not create Cognito account. Please try again.")

    # 3. Set permanent password
    try:
        cognito.admin_set_user_password(
            UserPoolId=settings.cognito_user_pool_id,
            Username=body.contact_email,
            Password=temp_password,
            Permanent=True,
        )
    except ClientError as e:
        cognito.admin_delete_user(
            UserPoolId=settings.cognito_user_pool_id, Username=body.contact_email
        )
        logger.error("admin_set_user_password failed: %s", e)
        raise HTTPException(500, "Could not set password. Please try again.")

    # 4. Add to publishers group
    cognito.admin_add_user_to_group(
        UserPoolId=settings.cognito_user_pool_id,
        Username=body.contact_email,
        GroupName="publishers",
    )

    # 5. Create FeedSource
    priority = 30 if body.source_type == "publisher" else 10   # publisher > aggregator
    source = FeedSource(
        name=body.company_name,
        source_type=body.source_type,
        priority=priority,
        cognito_sub=cognito_sub,
        contact_email=body.contact_email,
        distributor_code=body.distributor_code,
        managed_by="publisher",
    )
    db.add(source)
    await db.commit()
    await db.refresh(source)

    # 6. Send welcome email (fire-and-forget)
    import asyncio
    asyncio.create_task(
        send_publisher_invite_email(
            publisher_email=body.contact_email,
            contact_name=body.contact_name,
            company_name=body.company_name,
            temp_password=temp_password,
        )
    )

    return PublisherCreateOut(
        feed_source=PublisherOut.model_validate(source),
        temp_password=temp_password,
    )


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
