"""
ARC (Advance Reading Copy) service.

Handles:
- Generating presigned PUT URLs for publishers to upload ARC files
- Submitting ARC requests (retailers or trade contacts)
- Publisher approve/decline flow (decline requires a reason)
- Generating time-limited presigned GET URLs for approved requesters
"""
import logging
import uuid
from datetime import datetime, timedelta, timezone

import boto3
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import get_settings
from app.models.book import Book
from app.models.portal import ArcRequest, FeedSource
from app.schemas.arc import ArcDecision, ArcRequestCreate

logger = logging.getLogger(__name__)

ARC_EXPIRY_DAYS = 30         # approved download links valid for 30 days
ARC_UPLOAD_EXPIRES = 3600    # presigned PUT URL valid for 1 hour
ARC_DOWNLOAD_EXPIRES = 3600  # presigned GET URL valid for 1 hour


# ── Publisher: ARC file management ────────────────────────────────────────────

def generate_arc_upload_url(isbn13: str) -> tuple[str, str]:
    """
    Generate a presigned S3 PUT URL for uploading an ARC file.
    Returns (upload_url, s3_key).
    """
    settings = get_settings()
    s3_key = f"arcs/{isbn13}/arc.pdf"
    s3 = boto3.client("s3", region_name=settings.aws_region)
    url = s3.generate_presigned_url(
        "put_object",
        Params={
            "Bucket": settings.assets_bucket_name,
            "Key": s3_key,
            "ContentType": "application/pdf",
        },
        ExpiresIn=ARC_UPLOAD_EXPIRES,
    )
    return url, s3_key


def generate_arc_download_url(s3_key: str) -> str:
    """Generate a time-limited presigned GET URL for an approved ARC download."""
    settings = get_settings()
    s3 = boto3.client("s3", region_name=settings.aws_region)
    return s3.generate_presigned_url(
        "get_object",
        Params={
            "Bucket": settings.assets_bucket_name,
            "Key": s3_key,
        },
        ExpiresIn=ARC_DOWNLOAD_EXPIRES,
    )


def delete_arc_from_s3(isbn13: str) -> None:
    """Best-effort delete of the ARC file from S3."""
    settings = get_settings()
    s3 = boto3.client("s3", region_name=settings.aws_region)
    try:
        s3.delete_object(Bucket=settings.assets_bucket_name, Key=f"arcs/{isbn13}/arc.pdf")
    except Exception:
        pass


# ── Request submission ─────────────────────────────────────────────────────────

async def submit_arc_request(
    session: AsyncSession,
    book: Book,
    payload: ArcRequestCreate,
    retailer_id: uuid.UUID | None,
) -> ArcRequest:
    """
    Create an ARC request for a title.
    Raises ValueError if ARC requests are not enabled for the title.
    """
    if not book.arc_enabled:
        raise ValueError("ARC requests are not enabled for this title")

    # Prevent duplicate pending/approved requests from the same email
    existing = await session.scalar(
        select(ArcRequest).where(
            ArcRequest.book_id == book.id,
            ArcRequest.requester_email == payload.requester_email,
            ArcRequest.status.in_(["pending", "approved"]),
        )
    )
    if existing:
        raise ValueError("An active ARC request already exists for this email and title")

    # Resolve the publisher's feed source for routing notifications
    feed_source_id: uuid.UUID | None = None
    if book.publisher_id:
        fs = await session.scalar(
            select(FeedSource).where(
                FeedSource.source_type == "publisher",
                FeedSource.active == True,
            ).limit(1)
        )
        if fs:
            feed_source_id = fs.id

    arc = ArcRequest(
        id=uuid.uuid4(),
        book_id=book.id,
        feed_source_id=feed_source_id,
        requester_retailer_id=retailer_id,
        requester_type=payload.requester_type,
        requester_name=payload.requester_name,
        requester_email=str(payload.requester_email),
        requester_company=payload.requester_company,
        requester_message=payload.requester_message,
        status="pending",
    )
    session.add(arc)
    await session.flush()
    await session.refresh(arc)
    return arc


# ── Publisher: list requests ───────────────────────────────────────────────────

async def list_arc_requests(
    session: AsyncSession,
    feed_source_id: uuid.UUID,
    status: str | None = None,
    limit: int = 50,
    offset: int = 0,
) -> tuple[list[ArcRequest], int, int]:
    """
    Return (requests, total, pending_count) for a publisher's feed source.
    Ordered: pending first, then by created_at desc.
    """
    base = select(ArcRequest).where(ArcRequest.feed_source_id == feed_source_id)
    if status:
        base = base.where(ArcRequest.status == status)

    total = await session.scalar(
        select(func.count()).select_from(base.subquery())
    ) or 0

    pending_count = await session.scalar(
        select(func.count()).where(
            ArcRequest.feed_source_id == feed_source_id,
            ArcRequest.status == "pending",
        )
    ) or 0

    rows = (await session.scalars(
        base.order_by(
            (ArcRequest.status == "pending").desc(),
            ArcRequest.created_at.desc(),
        ).limit(limit).offset(offset)
    )).all()

    return list(rows), total, pending_count


# ── Publisher: decide ──────────────────────────────────────────────────────────

async def decide_arc_request(
    session: AsyncSession,
    arc: ArcRequest,
    decision: ArcDecision,
    reviewer_sub: str,
) -> ArcRequest:
    """
    Approve or decline an ARC request.
    Decline without a reason raises ValueError.
    """
    if arc.status != "pending":
        raise ValueError(f"Cannot act on a request with status '{arc.status}'")

    if decision.action == "decline":
        if not decision.decline_reason or not decision.decline_reason.strip():
            raise ValueError("A reason is required when declining an ARC request")
        arc.status = "declined"
        arc.decline_reason = decision.decline_reason.strip()
    else:
        arc.status = "approved"
        arc.approved_expires_at = datetime.now(timezone.utc).replace(tzinfo=None) + timedelta(days=ARC_EXPIRY_DAYS)

    arc.reviewed_by = reviewer_sub
    arc.reviewed_at = datetime.now(timezone.utc).replace(tzinfo=None)
    await session.flush()
    await session.refresh(arc)
    return arc


# ── Requester: check status ────────────────────────────────────────────────────

async def get_requester_status(
    session: AsyncSession,
    book_id: uuid.UUID,
    requester_email: str,
    book_arc_s3_key: str | None,
) -> dict:
    """
    Return the latest ARC request status for a given email + title combination.
    If approved and not expired, includes a fresh presigned download URL.
    """
    arc = await session.scalar(
        select(ArcRequest).where(
            ArcRequest.book_id == book_id,
            ArcRequest.requester_email == requester_email,
        ).order_by(ArcRequest.created_at.desc()).limit(1)
    )

    if not arc:
        return {"has_request": False, "status": None, "decline_reason": None, "download_url": None}

    download_url = None
    if (
        arc.status == "approved"
        and book_arc_s3_key
        and arc.approved_expires_at
        and arc.approved_expires_at > datetime.now(timezone.utc).replace(tzinfo=None)
    ):
        try:
            download_url = generate_arc_download_url(book_arc_s3_key)
        except Exception:
            pass

    return {
        "has_request": True,
        "status": arc.status,
        "decline_reason": arc.decline_reason,
        "download_url": download_url,
    }
