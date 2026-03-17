"""ONIX ingest API endpoints.

POST /api/v1/onix/ingest  — upload an ONIX 3.0 file for immediate ingestion
GET  /api/v1/onix/feeds   — list feed ingestion history
GET  /api/v1/onix/feeds/{feed_id} — single feed status/detail

Access: admin group only (Cognito group "admins").
"""
from __future__ import annotations

import uuid

from fastapi import APIRouter, Depends, File, HTTPException, Query, UploadFile
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_db, require_admin
from app.models.onix_feed import OnixFeed
from app.schemas.onix import OnixFeedListResponse, OnixFeedSummary, OnixIngestResponse
from app.services.onix_service import ingest_onix

router = APIRouter(prefix="/onix", tags=["onix"])

# Max upload size: 50 MB (large feeds come via S3, not direct upload)
_MAX_UPLOAD_BYTES = 50 * 1024 * 1024


@router.post("/ingest", response_model=OnixIngestResponse, status_code=202)
async def ingest_onix_upload(
    file: UploadFile = File(..., description="ONIX 3.0 XML file"),
    db: AsyncSession = Depends(get_db),
    _admin=Depends(require_admin),
):
    """
    Upload and immediately ingest an ONIX 3.0 file.

    Processes the file synchronously and returns a summary of what was ingested.
    For large production feeds (>50 MB) use S3-triggered ingestion instead.
    """
    if file.content_type not in (
        "text/xml", "application/xml", "application/octet-stream", None
    ):
        raise HTTPException(400, "File must be XML")

    content = await file.read()
    if len(content) > _MAX_UPLOAD_BYTES:
        raise HTTPException(413, f"File exceeds {_MAX_UPLOAD_BYTES // 1024 // 1024} MB limit")

    result = await ingest_onix(
        db,
        content,
        triggered_by="api-upload",
        s3_bucket="direct-upload",
        s3_key=file.filename or "unknown",
    )
    await db.commit()

    return OnixIngestResponse(**result)


@router.get("/feeds", response_model=OnixFeedListResponse)
async def list_feeds(
    limit: int = Query(20, ge=1, le=100),
    offset: int = Query(0, ge=0),
    db: AsyncSession = Depends(get_db),
    _admin=Depends(require_admin),
):
    """List ONIX feed ingestion history, newest first."""
    total_result = await db.execute(select(func.count()).select_from(OnixFeed))
    total = total_result.scalar_one()

    feeds_result = await db.execute(
        select(OnixFeed).order_by(OnixFeed.created_at.desc()).limit(limit).offset(offset)
    )
    feeds = feeds_result.scalars().all()

    return OnixFeedListResponse(
        feeds=[OnixFeedSummary.model_validate(f) for f in feeds],
        total=total,
    )


@router.get("/feeds/{feed_id}", response_model=OnixFeedSummary)
async def get_feed(
    feed_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    _admin=Depends(require_admin),
):
    """Get status and detail for a single ONIX feed run."""
    result = await db.execute(select(OnixFeed).where(OnixFeed.id == feed_id))
    feed = result.scalar_one_or_none()
    if feed is None:
        raise HTTPException(404, "Feed not found")
    return OnixFeedSummary.model_validate(feed)
