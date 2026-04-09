"""
Retailer account management endpoints.

Retailers sign in via the same Cognito pool as all users, but are in the
'retailers' group. On first call to GET /retailer/me, a Retailer row is
auto-created from their JWT claims — no separate registration step required.

Linking a distributor account creates a *pending* request. The distributor
must approve via POST /distributor/requests/{id}/approve before the link
becomes active. Retailers can withdraw pending or rejected requests.
"""
import uuid
import logging

import boto3
from botocore.exceptions import ClientError
from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_db, require_retailer
from app.auth.models import CurrentUser
from app.config import get_settings
from app.connectors.registry import get_connector, list_connectors
from app.models.retailer import Retailer, RetailerDistributor
from app.schemas.retailer import (
    DistributorOption,
    LinkAccountRequest,
    LinkedAccountOut,
    RegisterRequest,
    RetailerProfileOut,
    UpdateProfileRequest,
)
from app.services.email_service import notify_distributor_new_request, send_welcome_email

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/retailer", tags=["retailer"])


# ─── Helpers ──────────────────────────────────────────────────────────────────

def _cognito_email(sub: str) -> str:
    """Look up the user's email from Cognito by sub (username).

    Cognito access tokens don't include the email claim, so on first login
    we fetch it directly. Returns empty string on any error.
    """
    settings = get_settings()
    try:
        client = boto3.client("cognito-idp", region_name=settings.cognito_region)
        response = client.admin_get_user(
            UserPoolId=settings.cognito_user_pool_id,
            Username=sub,
        )
        attrs = {a["Name"]: a["Value"] for a in response["UserAttributes"]}
        return attrs.get("email", "")
    except ClientError as e:
        logger.warning("Could not fetch email from Cognito for sub=%s: %s", sub, e)
        return ""


async def _get_or_create_retailer(
    db: AsyncSession,
    user: CurrentUser,
) -> Retailer:
    """Return the Retailer row for this user, creating it on first login."""
    retailer = (
        await db.execute(select(Retailer).where(Retailer.cognito_sub == user.sub))
    ).scalar_one_or_none()

    if retailer is None:
        # Access tokens don't carry email — fetch from Cognito on first login
        email = user.email or _cognito_email(user.sub)
        retailer = Retailer(
            cognito_sub=user.sub,
            email=email,
            company_name=email,  # placeholder — updated via PATCH /retailer/me
        )
        db.add(retailer)
        await db.flush()
        logger.info("Auto-created Retailer record for %s", email)

    return retailer


def _distributor_name(code: str) -> str:
    try:
        return get_connector(code).distributor_name
    except ValueError:
        return code


def _account_out(account: RetailerDistributor) -> LinkedAccountOut:
    return LinkedAccountOut(
        id=account.id,
        distributor_code=account.distributor_code,
        distributor_name=_distributor_name(account.distributor_code),
        account_number=account.account_number,
        status=account.status,
        rejection_reason=account.rejection_reason,
        gratis_enabled=account.gratis_enabled,
        created_at=account.created_at,
    )


# ─── Background email tasks ───────────────────────────────────────────────────

async def _email_distributor_new_request(
    retailer: Retailer,
    account: RetailerDistributor,
) -> None:
    settings = get_settings()
    await notify_distributor_new_request(
        distributor_email=settings.ses_admin_email,  # → distributor contact email when distributor logins are built
        distributor_name=_distributor_name(account.distributor_code),
        retailer_company=retailer.company_name,
        retailer_email=retailer.email,
        account_number=account.account_number,
        request_id=str(account.id),
    )


# ─── Endpoints ────────────────────────────────────────────────────────────────

@router.post("/register", status_code=201)
async def register_retailer(
    body: RegisterRequest,
    background_tasks: BackgroundTasks,
    db: AsyncSession = Depends(get_db),
) -> dict:
    """
    Public endpoint — no auth required.
    Creates a Cognito user, adds them to the retailers group, creates
    the Retailer DB row, and sends a welcome email.
    """
    settings = get_settings()
    cognito = boto3.client("cognito-idp", region_name=settings.aws_region)

    # 1. Check email not already registered in our DB
    existing = await db.execute(
        select(Retailer).where(Retailer.email == body.email)
    )
    if existing.scalar_one_or_none():
        raise HTTPException(status_code=409, detail="An account with this email already exists.")

    # 2. Create Cognito user
    try:
        resp = cognito.admin_create_user(
            UserPoolId=settings.cognito_user_pool_id,
            Username=body.email,
            UserAttributes=[
                {"Name": "email", "Value": body.email},
                {"Name": "email_verified", "Value": "true"},
                {"Name": "name", "Value": body.contact_name},
            ],
            MessageAction="SUPPRESS",  # we send our own welcome email
        )
        cognito_sub = next(
            a["Value"] for a in resp["User"]["Attributes"] if a["Name"] == "sub"
        )
    except ClientError as e:
        code = e.response["Error"]["Code"]
        if code == "UsernameExistsException":
            raise HTTPException(status_code=409, detail="An account with this email already exists.")
        logger.error("Cognito admin_create_user failed: %s", e)
        raise HTTPException(status_code=500, detail="Could not create account. Please try again.")

    # 3. Set permanent password (skips FORCE_CHANGE_PASSWORD state)
    try:
        cognito.admin_set_user_password(
            UserPoolId=settings.cognito_user_pool_id,
            Username=body.email,
            Password=body.password,
            Permanent=True,
        )
    except ClientError as e:
        # Clean up the user we just created
        cognito.admin_delete_user(UserPoolId=settings.cognito_user_pool_id, Username=body.email)
        code = e.response["Error"]["Code"]
        if code == "InvalidPasswordException":
            raise HTTPException(status_code=422, detail="Password does not meet the requirements.")
        raise HTTPException(status_code=500, detail="Could not set password. Please try again.")

    # 4. Add to retailers group
    cognito.admin_add_user_to_group(
        UserPoolId=settings.cognito_user_pool_id,
        Username=body.email,
        GroupName="retailers",
    )

    # 5. Create retailer profile in DB
    retailer = Retailer(
        cognito_sub=cognito_sub,
        email=body.email,
        company_name=body.company_name,
        contact_name=body.contact_name,
        phone=body.phone,
        role=body.role,
        country_code=body.country_code,
        referral_source=body.referral_source,
    )
    db.add(retailer)
    await db.commit()

    # 6. Send welcome email in background
    background_tasks.add_task(
        send_welcome_email,
        retailer_email=body.email,
        contact_name=body.contact_name,
        company_name=body.company_name,
    )

    return {"success": True, "sub": cognito_sub}

@router.get("/me", response_model=RetailerProfileOut)
async def get_me(
    db: AsyncSession = Depends(get_db),
    current_user: CurrentUser = Depends(require_retailer),
) -> RetailerProfileOut:
    """Return the retailer's profile and all linked distributor accounts."""
    retailer = await _get_or_create_retailer(db, current_user)
    await db.commit()

    accounts = (
        await db.execute(
            select(RetailerDistributor)
            .where(
                RetailerDistributor.retailer_id == retailer.id,
                RetailerDistributor.status != "withdrawn",
            )
            .order_by(RetailerDistributor.created_at)
        )
    ).scalars().all()

    return RetailerProfileOut(
        id=retailer.id,
        company_name=retailer.company_name,
        email=retailer.email,
        country_code=retailer.country_code,
        san=retailer.san,
        plan=retailer.plan,
        plan_activated_at=retailer.plan_activated_at,
        plan_expires_at=retailer.plan_expires_at,
        extra_seats=retailer.extra_seats,
        accounts=[_account_out(a) for a in accounts],
    )


@router.patch("/me", response_model=RetailerProfileOut)
async def update_profile(
    body: UpdateProfileRequest,
    db: AsyncSession = Depends(get_db),
    current_user: CurrentUser = Depends(require_retailer),
) -> RetailerProfileOut:
    """Update the retailer's profile — company_name, country_code, and/or san."""
    retailer = await _get_or_create_retailer(db, current_user)
    if body.company_name is not None:
        retailer.company_name = body.company_name.strip()
    if body.country_code is not None:
        retailer.country_code = body.country_code.strip().upper()
    if body.san is not None:
        retailer.san = body.san.strip() or None
    await db.commit()
    await db.refresh(retailer)

    accounts = (
        await db.execute(
            select(RetailerDistributor).where(
                RetailerDistributor.retailer_id == retailer.id,
                RetailerDistributor.status != "withdrawn",
            )
        )
    ).scalars().all()

    return RetailerProfileOut(
        id=retailer.id,
        company_name=retailer.company_name,
        email=retailer.email,
        country_code=retailer.country_code,
        san=retailer.san,
        plan=retailer.plan,
        plan_activated_at=retailer.plan_activated_at,
        plan_expires_at=retailer.plan_expires_at,
        extra_seats=retailer.extra_seats,
        accounts=[_account_out(a) for a in accounts],
    )


@router.get("/distributors", response_model=list[DistributorOption])
async def list_distributors(
    current_user: CurrentUser = Depends(require_retailer),
) -> list[DistributorOption]:
    """List all distributor connectors available to link."""
    options = []
    for code in list_connectors():
        try:
            connector = get_connector(code)
            options.append(DistributorOption(
                distributor_code=code,
                distributor_name=connector.distributor_name,
                requires_account_number=connector.requires_credentials,
            ))
        except Exception:
            pass
    return options


@router.post("/accounts", response_model=LinkedAccountOut, status_code=status.HTTP_201_CREATED)
async def request_account_link(
    body: LinkAccountRequest,
    background_tasks: BackgroundTasks,
    db: AsyncSession = Depends(get_db),
    current_user: CurrentUser = Depends(require_retailer),
) -> LinkedAccountOut:
    """
    Submit a request to link a distributor account.

    Creates a *pending* request. The distributor must approve it before the
    account becomes active. If a previous request for this distributor was
    rejected or withdrawn, it is resubmitted (status → pending).
    """
    try:
        get_connector(body.distributor_code)
    except ValueError:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Unknown distributor: {body.distributor_code}",
        )

    retailer = await _get_or_create_retailer(db, current_user)

    existing = (
        await db.execute(
            select(RetailerDistributor).where(
                RetailerDistributor.retailer_id == retailer.id,
                RetailerDistributor.distributor_code == body.distributor_code,
            )
        )
    ).scalar_one_or_none()

    if existing:
        if existing.status in ("pending", "approved"):
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail=f"A {existing.status} request for this distributor already exists",
            )
        # Re-submit a previously rejected or withdrawn request
        existing.status = "pending"
        existing.account_number = body.account_number
        existing.rejection_reason = None
        await db.commit()
        await db.refresh(existing)
        logger.info("Retailer %s resubmitted link request for %s", retailer.email, body.distributor_code)
        background_tasks.add_task(_email_distributor_new_request, retailer, existing)
        return _account_out(existing)

    account = RetailerDistributor(
        retailer_id=retailer.id,
        distributor_code=body.distributor_code,
        account_number=body.account_number,
        status="pending",
    )
    db.add(account)
    await db.commit()
    await db.refresh(account)

    logger.info(
        "Retailer %s submitted link request for distributor %s", retailer.email, body.distributor_code
    )
    background_tasks.add_task(_email_distributor_new_request, retailer, account)
    return _account_out(account)


@router.delete("/accounts/{account_id}", status_code=status.HTTP_204_NO_CONTENT)
async def withdraw_account_request(
    account_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    current_user: CurrentUser = Depends(require_retailer),
) -> None:
    """
    Withdraw a pending request, or unlink an approved account.

    Sets status to 'withdrawn'. Approved accounts that are withdrawn can be
    re-requested later.
    """
    retailer = await _get_or_create_retailer(db, current_user)

    account = (
        await db.execute(
            select(RetailerDistributor).where(
                RetailerDistributor.id == account_id,
                RetailerDistributor.retailer_id == retailer.id,
            )
        )
    ).scalar_one_or_none()

    if not account:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Account not found")

    account.status = "withdrawn"
    await db.commit()
