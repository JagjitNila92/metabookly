"""
Publisher account endpoints.

POST /publisher/register   — public self-service registration
GET  /publisher/me         — return the publisher's own feed source record
"""
import logging

import boto3
from botocore.exceptions import ClientError
from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_db, require_publisher
from app.auth.models import CurrentUser
from app.config import get_settings
from app.models.portal import FeedSource
from app.schemas.portal import FeedSourceOut, PublisherRegisterRequest
from app.services.email_service import send_publisher_welcome_email

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/publisher", tags=["publisher"])


@router.post("/register", status_code=201)
async def register_publisher(
    body: PublisherRegisterRequest,
    background_tasks: BackgroundTasks,
    db: AsyncSession = Depends(get_db),
) -> dict:
    """
    Public endpoint — no auth required.
    Creates a Cognito user in the 'publishers' group, creates the FeedSource
    DB record (free plan, source_type=publisher), and sends a welcome email.
    """
    settings = get_settings()
    cognito = boto3.client("cognito-idp", region_name=settings.aws_region)

    # 1. Check email not already registered as a feed source
    existing = await db.execute(
        select(FeedSource).where(FeedSource.contact_email == body.email)
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
            MessageAction="SUPPRESS",
        )
        cognito_sub = next(
            a["Value"] for a in resp["User"]["Attributes"] if a["Name"] == "sub"
        )
    except ClientError as e:
        code = e.response["Error"]["Code"]
        if code == "UsernameExistsException":
            raise HTTPException(status_code=409, detail="An account with this email already exists.")
        logger.error("Cognito admin_create_user failed for publisher: %s", e)
        raise HTTPException(status_code=500, detail="Could not create account. Please try again.")

    # 3. Set permanent password
    try:
        cognito.admin_set_user_password(
            UserPoolId=settings.cognito_user_pool_id,
            Username=body.email,
            Password=body.password,
            Permanent=True,
        )
    except ClientError as e:
        cognito.admin_delete_user(UserPoolId=settings.cognito_user_pool_id, Username=body.email)
        code = e.response["Error"]["Code"]
        if code == "InvalidPasswordException":
            raise HTTPException(status_code=422, detail="Password does not meet the requirements.")
        raise HTTPException(status_code=500, detail="Could not set password. Please try again.")

    # 4. Add to publishers group
    cognito.admin_add_user_to_group(
        UserPoolId=settings.cognito_user_pool_id,
        Username=body.email,
        GroupName="publishers",
    )

    # 5. Create FeedSource record (free plan, publisher priority=30)
    feed_source = FeedSource(
        cognito_sub=cognito_sub,
        name=body.company_name,
        source_type="publisher",
        priority=30,
        plan="free",
        contact_email=body.email,
        contact_name=body.contact_name,
        managed_by="publisher",
        active=True,
    )
    db.add(feed_source)
    await db.commit()

    # 6. Welcome email in background
    background_tasks.add_task(
        send_publisher_welcome_email,
        publisher_email=body.email,
        contact_name=body.contact_name,
        company_name=body.company_name,
    )

    logger.info("Publisher registered: %s (%s)", body.company_name, body.email)
    return {"success": True, "sub": cognito_sub}


@router.get("/me", response_model=FeedSourceOut)
async def get_publisher_me(
    db: AsyncSession = Depends(get_db),
    current_user: CurrentUser = Depends(require_publisher),
) -> FeedSourceOut:
    """Return the publisher's own feed source record."""
    source = (
        await db.execute(
            select(FeedSource).where(FeedSource.cognito_sub == current_user.sub)
        )
    ).scalar_one_or_none()

    if source is None:
        raise HTTPException(
            status_code=404,
            detail="No publisher account found. Contact support.",
        )
    return FeedSourceOut.model_validate(source)
