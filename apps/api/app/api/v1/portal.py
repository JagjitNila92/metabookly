"""
Publisher/distributor portal API endpoints.

All routes require the 'publishers' or 'admins' Cognito group.

Endpoints
─────────
POST /portal/upload-url                  Get pre-signed S3 URL for ONIX upload
POST /portal/feeds/{feed_id}/trigger     Trigger ingest after S3 upload
GET  /portal/feeds                       List my feeds (newest first)
GET  /portal/feeds/{feed_id}             Single feed status + sample errors

GET  /portal/conflicts                   List pending metadata conflicts
POST /portal/conflicts/{id}/resolve      Resolve a conflict
GET  /portal/conflicts/stats             Count by status

GET  /portal/books/{isbn13}/editorial    Get editorial layer for a book
PUT  /portal/books/{isbn13}/editorial    Update editorial layer

GET  /portal/suggestions                 List AI suggestions (grouped by confidence)
POST /portal/suggestions/bulk-accept     Bulk accept by confidence or ID list
POST /portal/suggestions/{id}/accept     Accept single suggestion
POST /portal/suggestions/{id}/reject     Reject single suggestion

GET  /portal/me                          My feed source record
"""
from __future__ import annotations

import hashlib
import logging
import secrets
import uuid
from datetime import datetime, UTC

import boto3

from fastapi import APIRouter, BackgroundTasks, Depends, File, HTTPException, Query, UploadFile, status
from sqlalchemy import func, select
from sqlalchemy.dialects.postgresql import insert as pg_insert
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_current_user, get_db, require_publisher
from app.auth.models import CurrentUser
from app.aws.s3 import delete_cover_from_s3, download_from_s3, generate_onix_upload_url, upload_cover_to_s3
from app.config import get_settings
from app.models.book import Book
from app.models.portal import (
    AiSuggestion,
    ArcRequest,
    BookEditorialLayer,
    BookMetadataVersion,
    FeedSource,
    FeedSourceApiKey,
    MetadataConflict,
    OnixFeedV2,
)
from app.schemas.portal import (
    AiSuggestionListResponse,
    AiSuggestionOut,
    ApiKeyCreated,
    ApiKeyOut,
    BookDetailOut,
    BookVersionOut,
    BulkAcceptRequest,
    BulkAcceptResponse,
    ConflictListResponse,
    ConflictOut,
    CreateApiKeyRequest,
    EditorialLayerOut,
    EditorialLayerUpdate,
    FeedSourceOut,
    FeedV2Detail,
    FeedV2ListResponse,
    FeedV2Summary,
    ResolveConflictRequest,
    TriggerIngestResponse,
    UploadUrlResponse,
)
from app.services.portal_service import ingest_onix_portal

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/portal", tags=["portal"])


# ─── Helpers ─────────────────────────────────────────────────────────────────

async def _get_feed_source(
    session: AsyncSession,
    current_user: CurrentUser,
) -> FeedSource | None:
    """Return the FeedSource linked to the current user's Cognito sub."""
    result = await session.execute(
        select(FeedSource).where(FeedSource.cognito_sub == current_user.sub)
    )
    return result.scalar_one_or_none()


async def _require_feed_source(
    session: AsyncSession,
    current_user: CurrentUser,
) -> FeedSource:
    source = await _get_feed_source(session, current_user)
    if source is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="No feed source linked to your account. Contact support.",
        )
    return source


# ─── Feed source identity ─────────────────────────────────────────────────────

@router.get("/me", response_model=FeedSourceOut)
async def get_my_feed_source(
    db: AsyncSession = Depends(get_db),
    current_user: CurrentUser = Depends(require_publisher),
) -> FeedSourceOut:
    """Return the feed source record linked to the current publisher account."""
    source = await _require_feed_source(db, current_user)
    return FeedSourceOut.model_validate(source)


# ─── Upload URL ───────────────────────────────────────────────────────────────

@router.post("/upload-url", response_model=UploadUrlResponse)
async def create_upload_url(
    filename: str = Query(..., description="Original filename e.g. catalog_2026_03.xml"),
    sequence_number: int | None = Query(None, description="Feed sequence number (optional)"),
    db: AsyncSession = Depends(get_db),
    current_user: CurrentUser = Depends(require_publisher),
) -> UploadUrlResponse:
    """
    Reserve a feed ID and return a pre-signed S3 PUT URL.

    The publisher uploads their ONIX file directly to S3 using the URL,
    then calls POST /portal/feeds/{feed_id}/trigger to start processing.

    URL is valid for 60 minutes.
    """
    settings = get_settings()
    feed_source = await _get_feed_source(db, current_user)
    feed_source_id = feed_source.id if feed_source else None

    feed_id = uuid.uuid4()
    # Key: {source_id}/{feed_id}/{filename} or onix-uploads/{feed_id}/{filename}
    prefix = str(feed_source_id) if feed_source_id else "unlinked"
    s3_key = f"uploads/{prefix}/{feed_id}/{filename}"

    # Create a pending OnixFeedV2 record so the feed_id is pre-allocated
    feed = OnixFeedV2(
        id=feed_id,
        feed_source_id=feed_source_id,
        s3_bucket=settings.onix_bucket_name,
        s3_key=s3_key,
        original_filename=filename,
        sequence_number=sequence_number,
        status="pending",
        triggered_by="portal_upload",
    )
    db.add(feed)
    await db.commit()

    upload_url = generate_onix_upload_url(s3_key, expires_in=3600)

    return UploadUrlResponse(
        feed_id=feed_id,
        upload_url=upload_url,
        s3_key=s3_key,
        expires_in_seconds=3600,
    )


# ─── Trigger ingest ───────────────────────────────────────────────────────────

async def _run_ingest_background(
    feed_id: uuid.UUID,
    feed_source_id: uuid.UUID | None,
    s3_bucket: str,
    s3_key: str,
    original_filename: str | None,
    sequence_number: int | None,
    triggered_by: str,
) -> None:
    """Background task: download from S3 and run the portal ingest pipeline."""
    from app.db.engine import get_session_factory
    async with get_session_factory()() as session:
        try:
            content = download_from_s3(s3_bucket, s3_key)
            await ingest_onix_portal(
                session,
                content,
                feed_source_id=feed_source_id,
                original_filename=original_filename,
                s3_bucket=s3_bucket,
                s3_key=s3_key,
                triggered_by=triggered_by,
                sequence_number=sequence_number,
            )
            await session.commit()
        except Exception:
            logger.exception("Background ingest failed for feed %s", feed_id)
            await session.rollback()
            # Mark feed as failed
            async with get_session_factory()() as err_session:
                result = await err_session.execute(
                    select(OnixFeedV2).where(OnixFeedV2.id == feed_id)
                )
                feed = result.scalar_one_or_none()
                if feed:
                    feed.status = "failed"
                    feed.error_detail = "Background worker exception"
                    feed.completed_at = datetime.now(UTC).replace(tzinfo=None)
                    await err_session.commit()


@router.post("/feeds/{feed_id}/trigger", response_model=TriggerIngestResponse, status_code=202)
async def trigger_ingest(
    feed_id: uuid.UUID,
    background_tasks: BackgroundTasks,
    db: AsyncSession = Depends(get_db),
    current_user: CurrentUser = Depends(require_publisher),
) -> TriggerIngestResponse:
    """
    Trigger processing of an ONIX file that has been uploaded to S3.

    Call this after you have PUT the file to the upload_url returned by POST /portal/upload-url.
    Returns 202 Accepted immediately — poll GET /portal/feeds/{feed_id} for progress.
    """
    result = await db.execute(select(OnixFeedV2).where(OnixFeedV2.id == feed_id))
    feed = result.scalar_one_or_none()
    if feed is None:
        raise HTTPException(status_code=404, detail="Feed not found")
    if feed.status not in ("pending", "failed"):
        raise HTTPException(
            status_code=409,
            detail=f"Feed is already {feed.status} — cannot re-trigger",
        )

    # Verify the feed belongs to this user's source (admins can trigger any)
    if not current_user.is_admin:
        source = await _get_feed_source(db, current_user)
        if source is None or feed.feed_source_id != source.id:
            raise HTTPException(status_code=403, detail="Not your feed")

    feed.status = "pending"  # reset if it was failed
    await db.commit()

    background_tasks.add_task(
        _run_ingest_background,
        feed_id=feed_id,
        feed_source_id=feed.feed_source_id,
        s3_bucket=feed.s3_bucket,
        s3_key=feed.s3_key,
        original_filename=feed.original_filename,
        sequence_number=feed.sequence_number,
        triggered_by="portal_trigger",
    )

    return TriggerIngestResponse(feed_id=feed_id, status="processing")


# ─── Feed history ─────────────────────────────────────────────────────────────

@router.get("/feeds", response_model=FeedV2ListResponse)
async def list_my_feeds(
    limit: int = Query(20, ge=1, le=100),
    offset: int = Query(0, ge=0),
    db: AsyncSession = Depends(get_db),
    current_user: CurrentUser = Depends(require_publisher),
) -> FeedV2ListResponse:
    """List feeds submitted by the current publisher, newest first."""
    source = await _get_feed_source(db, current_user)

    base_filter = (
        OnixFeedV2.feed_source_id == source.id
        if (source and not current_user.is_admin)
        else True  # admins see all
    )

    total = (
        await db.execute(select(func.count()).select_from(OnixFeedV2).where(base_filter))
    ).scalar_one()

    feeds = (
        await db.execute(
            select(OnixFeedV2)
            .where(base_filter)
            .order_by(OnixFeedV2.created_at.desc())
            .limit(limit)
            .offset(offset)
        )
    ).scalars().all()

    return FeedV2ListResponse(
        feeds=[FeedV2Summary.model_validate(f) for f in feeds],
        total=total,
    )


@router.get("/feeds/{feed_id}", response_model=FeedV2Detail)
async def get_feed(
    feed_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    current_user: CurrentUser = Depends(require_publisher),
) -> FeedV2Detail:
    """Get status and sample errors for a single feed run."""
    result = await db.execute(select(OnixFeedV2).where(OnixFeedV2.id == feed_id))
    feed = result.scalar_one_or_none()
    if feed is None:
        raise HTTPException(404, "Feed not found")

    if not current_user.is_admin:
        source = await _get_feed_source(db, current_user)
        if source is None or feed.feed_source_id != source.id:
            raise HTTPException(403, "Not your feed")

    return FeedV2Detail.model_validate(feed)


# ─── Conflicts ────────────────────────────────────────────────────────────────

@router.get("/conflicts", response_model=ConflictListResponse)
async def list_conflicts(
    status_filter: str = Query("pending", alias="status"),
    limit: int = Query(20, ge=1, le=100),
    offset: int = Query(0, ge=0),
    db: AsyncSession = Depends(get_db),
    current_user: CurrentUser = Depends(require_publisher),
) -> ConflictListResponse:
    """List metadata conflicts for books from your feeds."""
    source = await _get_feed_source(db, current_user)

    # Filter to conflicts raised by this source's feeds
    stmt_base = select(MetadataConflict).where(
        MetadataConflict.status == status_filter
    )
    if source and not current_user.is_admin:
        # Sub-query: only conflicts from this publisher's feeds
        my_feed_ids = select(OnixFeedV2.id).where(
            OnixFeedV2.feed_source_id == source.id
        )
        stmt_base = stmt_base.where(MetadataConflict.feed_id.in_(my_feed_ids))

    total = (
        await db.execute(
            select(func.count()).select_from(MetadataConflict)
            .where(MetadataConflict.status == status_filter)
        )
    ).scalar_one()

    conflicts = (
        await db.execute(
            stmt_base.order_by(MetadataConflict.created_at.desc())
            .limit(limit).offset(offset)
        )
    ).scalars().all()

    return ConflictListResponse(
        conflicts=[ConflictOut.model_validate(c) for c in conflicts],
        total=total,
    )


@router.post("/conflicts/{conflict_id}/resolve", response_model=ConflictOut)
async def resolve_conflict(
    conflict_id: uuid.UUID,
    body: ResolveConflictRequest,
    db: AsyncSession = Depends(get_db),
    current_user: CurrentUser = Depends(require_publisher),
) -> ConflictOut:
    """
    Resolve a pending metadata conflict.

    resolution: "accept_onix" — apply the feed's value to the editorial layer
    resolution: "keep_editorial" — discard the feed's value, keep existing editorial
    """
    if body.resolution not in ("accept_onix", "keep_editorial"):
        raise HTTPException(400, "resolution must be 'accept_onix' or 'keep_editorial'")

    result = await db.execute(
        select(MetadataConflict).where(MetadataConflict.id == conflict_id)
    )
    conflict = result.scalar_one_or_none()
    if conflict is None:
        raise HTTPException(404, "Conflict not found")
    if conflict.status != "pending":
        raise HTTPException(409, f"Conflict already resolved: {conflict.status}")

    if body.resolution == "accept_onix":
        # Apply the ONIX value to the editorial layer
        layer_result = await db.execute(
            select(BookEditorialLayer).where(
                BookEditorialLayer.book_id == conflict.book_id
            )
        )
        layer = layer_result.scalar_one_or_none()
        if layer:
            setattr(layer, conflict.field_name, conflict.onix_value)
            sources = dict(layer.field_sources or {})
            sources[conflict.field_name] = "onix"
            layer.field_sources = sources
            layer.edited_by = current_user.sub

    conflict.status = "accepted_onix" if body.resolution == "accept_onix" else "kept_editorial"
    conflict.resolved_by = current_user.sub
    conflict.resolved_at = datetime.now(UTC).replace(tzinfo=None)
    await db.commit()
    await db.refresh(conflict)
    return ConflictOut.model_validate(conflict)


# ─── Editorial layer ──────────────────────────────────────────────────────────

@router.get("/books/{isbn13}/editorial", response_model=EditorialLayerOut)
async def get_editorial_layer(
    isbn13: str,
    db: AsyncSession = Depends(get_db),
    current_user: CurrentUser = Depends(require_publisher),
) -> EditorialLayerOut:
    """Get the editorial metadata layer for a book."""
    book = (
        await db.execute(select(Book).where(Book.isbn13 == isbn13))
    ).scalar_one_or_none()
    if book is None:
        raise HTTPException(404, "Book not found")

    layer = (
        await db.execute(
            select(BookEditorialLayer).where(BookEditorialLayer.book_id == book.id)
        )
    ).scalar_one_or_none()

    if layer is None:
        # Return an empty layer — caller can PUT to create it
        raise HTTPException(404, "No editorial layer exists for this book yet")

    return EditorialLayerOut.model_validate(layer)


@router.put("/books/{isbn13}/editorial", response_model=EditorialLayerOut)
async def update_editorial_layer(
    isbn13: str,
    body: EditorialLayerUpdate,
    db: AsyncSession = Depends(get_db),
    current_user: CurrentUser = Depends(require_publisher),
) -> EditorialLayerOut:
    """
    Create or update the editorial layer for a book.

    Fields set here are protected from ONIX overwrite — the feed update
    will go to the conflicts inbox instead of being applied automatically.
    """
    book = (
        await db.execute(select(Book).where(Book.isbn13 == isbn13))
    ).scalar_one_or_none()
    if book is None:
        raise HTTPException(404, "Book not found")

    layer_result = await db.execute(
        select(BookEditorialLayer).where(BookEditorialLayer.book_id == book.id)
    )
    layer = layer_result.scalar_one_or_none()

    update_data = body.model_dump(exclude_none=True)
    field_sources: dict[str, str] = {}

    if layer is None:
        # Create new layer
        layer = BookEditorialLayer(
            book_id=book.id,
            edited_by=current_user.sub,
        )
        db.add(layer)
    else:
        layer.edited_by = current_user.sub
        field_sources = dict(layer.field_sources or {})

    for field, value in update_data.items():
        setattr(layer, field, value)
        field_sources[field] = "editorial"

    layer.field_sources = field_sources
    await db.commit()
    await db.refresh(layer)
    return EditorialLayerOut.model_validate(layer)


# ─── Book detail ──────────────────────────────────────────────────────────────

@router.get("/books/{isbn13}", response_model=BookDetailOut)
async def get_book_detail(
    isbn13: str,
    db: AsyncSession = Depends(get_db),
    current_user: CurrentUser = Depends(require_publisher),
) -> BookDetailOut:
    """
    Return the full merged book record for the portal book detail page.
    Combines ONIX-sourced fields with any editorial layer overrides, and
    exposes the original ONIX values so the UI can show what changed.
    """
    book = (
        await db.execute(select(Book).where(Book.isbn13 == isbn13))
    ).scalar_one_or_none()
    if book is None:
        raise HTTPException(404, "Book not found")

    layer = (
        await db.execute(
            select(BookEditorialLayer).where(BookEditorialLayer.book_id == book.id)
        )
    ).scalar_one_or_none()

    field_sources = dict(layer.field_sources or {}) if layer else {}

    # Effective values: editorial override wins, falls back to ONIX
    eff_description = (layer.description if layer and layer.description else book.description)
    eff_toc         = (layer.toc if layer and layer.toc else book.toc)
    eff_excerpt     = (layer.excerpt if layer and layer.excerpt else book.excerpt)

    return BookDetailOut(
        isbn13=book.isbn13,
        isbn10=book.isbn10,
        title=book.title,
        subtitle=book.subtitle,
        product_form=book.product_form,
        page_count=book.page_count,
        publication_date=book.publication_date.isoformat() if book.publication_date else None,
        publishing_status=book.publishing_status,
        uk_rights=book.uk_rights,
        rrp_gbp=str(book.rrp_gbp) if book.rrp_gbp else None,
        rrp_usd=str(book.rrp_usd) if book.rrp_usd else None,
        cover_image_url=book.cover_image_url,
        height_mm=book.height_mm,
        width_mm=book.width_mm,
        metadata_score=book.metadata_score,
        description=eff_description,
        toc=eff_toc,
        excerpt=eff_excerpt,
        field_sources=field_sources,
        onix_description=book.description,
        onix_toc=book.toc,
        onix_excerpt=book.excerpt,
    )


# ─── Cover image upload ───────────────────────────────────────────────────────

_ALLOWED_COVER_TYPES = {"image/jpeg", "image/png"}
_MAX_COVER_BYTES = 10 * 1024 * 1024  # 10 MB


@router.post("/books/{isbn13}/cover", status_code=200)
async def upload_cover(
    isbn13: str,
    file: UploadFile = File(...),
    db: AsyncSession = Depends(get_db),
    current_user: CurrentUser = Depends(require_publisher),
) -> dict:
    """
    Upload a cover image for a book directly (separate from ONIX).

    Accepts JPEG or PNG, max 10 MB. The image is stored in the assets S3 bucket
    and books.cover_image_url is updated immediately.
    """
    book = (
        await db.execute(select(Book).where(Book.isbn13 == isbn13))
    ).scalar_one_or_none()
    if book is None:
        raise HTTPException(404, "Book not found")

    content_type = file.content_type or ""
    if content_type not in _ALLOWED_COVER_TYPES:
        raise HTTPException(400, "Only JPEG and PNG images are accepted")

    content = await file.read()
    if len(content) > _MAX_COVER_BYTES:
        raise HTTPException(400, "File exceeds 10 MB limit")

    cover_url = upload_cover_to_s3(isbn13, content, content_type)
    book.cover_image_url = cover_url
    await db.commit()

    return {"cover_image_url": cover_url}


@router.delete("/books/{isbn13}/cover", status_code=204, response_model=None)
async def delete_cover(
    isbn13: str,
    db: AsyncSession = Depends(get_db),
    current_user: CurrentUser = Depends(require_publisher),
) -> None:
    """
    Remove the manually uploaded cover for a book.

    Deletes the S3 object and clears books.cover_image_url.
    The next ONIX ingest will restore the ONIX-supplied cover URL if one exists.
    """
    book = (
        await db.execute(select(Book).where(Book.isbn13 == isbn13))
    ).scalar_one_or_none()
    if book is None:
        raise HTTPException(404, "Book not found")

    delete_cover_from_s3(isbn13)
    book.cover_image_url = None
    await db.commit()


# ─── Version history ──────────────────────────────────────────────────────────

@router.get("/books/{isbn13}/versions", response_model=list[BookVersionOut])
async def list_book_versions(
    isbn13: str,
    db: AsyncSession = Depends(get_db),
    current_user: CurrentUser = Depends(require_publisher),
) -> list[BookVersionOut]:
    """List version history for a book (newest first, max 50)."""
    book = (
        await db.execute(select(Book).where(Book.isbn13 == isbn13))
    ).scalar_one_or_none()
    if book is None:
        raise HTTPException(404, "Book not found")

    versions = (
        await db.execute(
            select(BookMetadataVersion)
            .where(BookMetadataVersion.book_id == book.id)
            .order_by(BookMetadataVersion.version_number.desc())
            .limit(50)
        )
    ).scalars().all()

    return [BookVersionOut.model_validate(v) for v in versions]


@router.post("/books/{isbn13}/versions/{version_id}/restore", status_code=200)
async def restore_book_version(
    isbn13: str,
    version_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    current_user: CurrentUser = Depends(require_publisher),
) -> dict:
    """
    Restore a book to a previous snapshot.

    Applies the snapshot fields back to the Book record and writes a new version
    entry so the restore itself is tracked in the audit trail.
    """
    book = (
        await db.execute(select(Book).where(Book.isbn13 == isbn13))
    ).scalar_one_or_none()
    if book is None:
        raise HTTPException(404, "Book not found")

    version = (
        await db.execute(
            select(BookMetadataVersion).where(
                BookMetadataVersion.id == version_id,
                BookMetadataVersion.book_id == book.id,
            )
        )
    ).scalar_one_or_none()
    if version is None:
        raise HTTPException(404, "Version not found")

    # Restorable text fields from the snapshot
    restorable = ("title", "subtitle", "description", "toc", "excerpt",
                  "product_form", "page_count", "publishing_status", "uk_rights")
    snap = version.snapshot
    for field in restorable:
        if field in snap:
            setattr(book, field, snap[field])

    # Write a new snapshot marking the restore
    from app.services.portal_service import _snapshot_book
    await _snapshot_book(db, book, changed_by=f"restore:{current_user.sub}:{version_id}")

    await db.commit()
    return {"restored_version": version.version_number, "isbn13": isbn13}


# ─── AI suggestions ───────────────────────────────────────────────────────────

@router.get("/suggestions", response_model=AiSuggestionListResponse)
async def list_suggestions(
    confidence: str | None = Query(None, description="Filter: high | medium | low"),
    limit: int = Query(50, ge=1, le=200),
    offset: int = Query(0, ge=0),
    db: AsyncSession = Depends(get_db),
    current_user: CurrentUser = Depends(require_publisher),
) -> AiSuggestionListResponse:
    """List pending AI metadata suggestions, optionally filtered by confidence."""
    filters = [AiSuggestion.status == "pending"]
    if confidence:
        filters.append(AiSuggestion.confidence == confidence)

    total = (
        await db.execute(
            select(func.count()).select_from(AiSuggestion).where(*filters)
        )
    ).scalar_one()

    suggestions = (
        await db.execute(
            select(AiSuggestion)
            .where(*filters)
            .order_by(AiSuggestion.confidence, AiSuggestion.created_at)
            .limit(limit).offset(offset)
        )
    ).scalars().all()

    # Count by confidence
    counts_result = await db.execute(
        select(AiSuggestion.confidence, func.count())
        .where(AiSuggestion.status == "pending")
        .group_by(AiSuggestion.confidence)
    )
    by_confidence = {row[0]: row[1] for row in counts_result.all()}

    return AiSuggestionListResponse(
        suggestions=[AiSuggestionOut.model_validate(s) for s in suggestions],
        total=total,
        by_confidence=by_confidence,
    )


@router.post("/suggestions/{suggestion_id}/accept", response_model=AiSuggestionOut)
async def accept_suggestion(
    suggestion_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    current_user: CurrentUser = Depends(require_publisher),
) -> AiSuggestionOut:
    """Accept a single AI suggestion — applies the value to the editorial layer."""
    result = await db.execute(
        select(AiSuggestion).where(AiSuggestion.id == suggestion_id)
    )
    suggestion = result.scalar_one_or_none()
    if suggestion is None:
        raise HTTPException(404, "Suggestion not found")
    if suggestion.status != "pending":
        raise HTTPException(409, f"Suggestion already {suggestion.status}")

    await _apply_suggestion(db, suggestion, current_user.sub, "accepted")
    await db.commit()
    await db.refresh(suggestion)
    return AiSuggestionOut.model_validate(suggestion)


@router.post("/suggestions/{suggestion_id}/reject", response_model=AiSuggestionOut)
async def reject_suggestion(
    suggestion_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    current_user: CurrentUser = Depends(require_publisher),
) -> AiSuggestionOut:
    """Reject a single AI suggestion — discards the suggested value."""
    result = await db.execute(
        select(AiSuggestion).where(AiSuggestion.id == suggestion_id)
    )
    suggestion = result.scalar_one_or_none()
    if suggestion is None:
        raise HTTPException(404, "Suggestion not found")
    if suggestion.status != "pending":
        raise HTTPException(409, f"Suggestion already {suggestion.status}")

    suggestion.status = "rejected"
    suggestion.reviewed_by = current_user.sub
    suggestion.reviewed_at = datetime.now(UTC).replace(tzinfo=None)
    await db.commit()
    await db.refresh(suggestion)
    return AiSuggestionOut.model_validate(suggestion)


@router.post("/suggestions/bulk-accept", response_model=BulkAcceptResponse)
async def bulk_accept_suggestions(
    body: BulkAcceptRequest,
    db: AsyncSession = Depends(get_db),
    current_user: CurrentUser = Depends(require_publisher),
) -> BulkAcceptResponse:
    """
    Bulk accept AI suggestions.

    Pass confidence="high" to accept all high-confidence pending suggestions.
    Pass ids=[...] to accept specific suggestions by ID.
    Pass both to accept all high-confidence AND specific IDs.
    """
    if not body.confidence and not body.ids:
        raise HTTPException(400, "Provide confidence and/or ids")

    filters = [AiSuggestion.status == "pending"]
    if body.confidence:
        filters.append(AiSuggestion.confidence == body.confidence)
    if body.ids:
        filters.append(AiSuggestion.id.in_(body.ids))

    pending = (
        await db.execute(select(AiSuggestion).where(*filters))
    ).scalars().all()

    accepted = 0
    for suggestion in pending:
        try:
            await _apply_suggestion(db, suggestion, current_user.sub, "accepted")
            accepted += 1
        except Exception:
            logger.exception("Failed to apply suggestion %s", suggestion.id)

    await db.commit()
    return BulkAcceptResponse(accepted=accepted, rejected=0)


@router.post("/suggestions/generate", status_code=202)
async def generate_suggestions(
    background_tasks: BackgroundTasks,
    field: str = Query("description", description="description | toc | excerpt"),
    limit: int = Query(20, ge=1, le=50),
    db: AsyncSession = Depends(get_db),
    current_user: CurrentUser = Depends(require_publisher),
) -> dict:
    """
    Trigger on-demand AI suggestion generation for a specific field.
    Runs in the background — returns immediately with 202 Accepted.
    """
    from app.services.ai_service import generate_field_suggestions, SupportedField

    if field not in ("description", "toc", "excerpt"):
        raise HTTPException(400, "field must be one of: description, toc, excerpt")

    source = await _require_feed_source(db, current_user)

    async def _run() -> None:
        from app.db.engine import get_session_factory
        async with get_session_factory()() as bg_session:
            try:
                count = await generate_field_suggestions(
                    bg_session, source.id, field=field, limit=limit  # type: ignore[arg-type]
                )
                await bg_session.commit()
                logger.info("Generated %d AI suggestions for field=%s source=%s", count, field, source.id)
            except Exception as exc:
                logger.warning("Background AI generation failed for field=%s: %s", field, exc)

    background_tasks.add_task(_run)
    return {"status": "generating", "field": field}


async def _apply_suggestion(
    db: AsyncSession,
    suggestion: AiSuggestion,
    reviewer_sub: str,
    new_status: str,
) -> None:
    """Apply an AI suggestion to the editorial layer and mark it reviewed."""
    if new_status == "accepted":
        # Upsert the editorial layer with the suggested value
        layer_result = await db.execute(
            select(BookEditorialLayer).where(
                BookEditorialLayer.book_id == suggestion.book_id
            )
        )
        layer = layer_result.scalar_one_or_none()
        if layer is None:
            layer = BookEditorialLayer(
                book_id=suggestion.book_id,
                edited_by=reviewer_sub,
                field_sources={suggestion.field_name: "ai_accepted"},
            )
            db.add(layer)
        else:
            sources = dict(layer.field_sources or {})
            sources[suggestion.field_name] = "ai_accepted"
            layer.field_sources = sources
            layer.edited_by = reviewer_sub

        if suggestion.field_name in ("description", "toc", "excerpt"):
            setattr(layer, suggestion.field_name, suggestion.suggested_value)

    suggestion.status = new_status
    suggestion.reviewed_by = reviewer_sub
    suggestion.reviewed_at = datetime.now(UTC).replace(tzinfo=None)


# ─── API key management ───────────────────────────────────────────────────────

def _hash_key(plaintext: str) -> str:
    """SHA-256 hash of the plaintext key for storage."""
    return hashlib.sha256(plaintext.encode()).hexdigest()


@router.post("/api-keys", response_model=ApiKeyCreated, status_code=201)
async def create_api_key(
    body: CreateApiKeyRequest,
    db: AsyncSession = Depends(get_db),
    current_user: CurrentUser = Depends(require_publisher),
) -> ApiKeyCreated:
    """
    Generate a new API key for programmatic ONIX uploads.
    The plaintext key is returned ONCE and never stored — save it immediately.
    """
    source = await _require_feed_source(db, current_user)

    # Enforce a cap of 5 active keys per source
    active_count = (
        await db.execute(
            select(func.count()).select_from(FeedSourceApiKey).where(
                FeedSourceApiKey.feed_source_id == source.id,
                FeedSourceApiKey.revoked == False,  # noqa: E712
            )
        )
    ).scalar_one()
    if active_count >= 5:
        raise HTTPException(
            status_code=409,
            detail="Maximum of 5 active API keys reached. Revoke one before creating another.",
        )

    # Generate a secure random key with a recognisable prefix
    raw = secrets.token_urlsafe(32)
    plaintext = f"mb_live_{raw}"
    key_prefix = plaintext[:16]  # "mb_live_" + first 8 chars

    key = FeedSourceApiKey(
        feed_source_id=source.id,
        key_hash=_hash_key(plaintext),
        key_prefix=key_prefix,
        label=body.label,
    )
    db.add(key)
    await db.commit()
    await db.refresh(key)

    return ApiKeyCreated(
        id=key.id,
        key_prefix=key.key_prefix,
        label=key.label,
        created_at=key.created_at,
        last_used_at=key.last_used_at,
        plaintext_key=plaintext,
    )


@router.get("/api-keys", response_model=list[ApiKeyOut])
async def list_api_keys(
    db: AsyncSession = Depends(get_db),
    current_user: CurrentUser = Depends(require_publisher),
) -> list[ApiKeyOut]:
    """List active API keys for the current publisher (never returns plaintext)."""
    source = await _require_feed_source(db, current_user)

    keys = (
        await db.execute(
            select(FeedSourceApiKey).where(
                FeedSourceApiKey.feed_source_id == source.id,
                FeedSourceApiKey.revoked == False,  # noqa: E712
            ).order_by(FeedSourceApiKey.created_at.desc())
        )
    ).scalars().all()

    return [ApiKeyOut.model_validate(k) for k in keys]


@router.delete("/api-keys/{key_prefix}", status_code=204, response_model=None)
async def revoke_api_key(
    key_prefix: str,
    db: AsyncSession = Depends(get_db),
    current_user: CurrentUser = Depends(require_publisher),
) -> None:
    """Revoke an API key by its prefix. Immediately invalidates the key."""
    source = await _require_feed_source(db, current_user)

    key = (
        await db.execute(
            select(FeedSourceApiKey).where(
                FeedSourceApiKey.key_prefix == key_prefix,
                FeedSourceApiKey.feed_source_id == source.id,
                FeedSourceApiKey.revoked == False,  # noqa: E712
            )
        )
    ).scalar_one_or_none()

    if key is None:
        raise HTTPException(status_code=404, detail="API key not found")

    key.revoked = True
    await db.commit()


@router.get("/quality")
async def get_quality_summary(
    db: AsyncSession = Depends(get_db),
    current_user: CurrentUser = Depends(require_publisher),
) -> dict:
    """
    Return metadata quality summary for the publisher's catalog.
    Includes average score, per-issue breakdown, and worst-scoring titles.
    """
    from app.services.metadata_quality import get_quality_summary

    source = await _require_feed_source(db, current_user)
    return await get_quality_summary(db, source.id)


# ── ARC endpoints (publisher side) ────────────────────────────────────────────

from app.schemas.arc import ArcDecision, ArcRequestOut, ArcRequestList, ArcUploadUrlOut, ArcUploadConfirm
from app.services import arc_service
from app.services.email_service import send_arc_approved, send_arc_declined


@router.get("/books/{isbn13}/arc/upload-url", response_model=ArcUploadUrlOut)
async def get_arc_upload_url(
    isbn13: str,
    db: AsyncSession = Depends(get_db),
    current_user: CurrentUser = Depends(require_publisher),
) -> ArcUploadUrlOut:
    """Generate a presigned S3 PUT URL for uploading an ARC PDF for a title."""
    source = await _require_feed_source(db, current_user)
    book = (await db.execute(select(Book).where(Book.isbn13 == isbn13))).scalar_one_or_none()
    if book is None:
        raise HTTPException(status_code=404, detail="Book not found")

    upload_url, s3_key = arc_service.generate_arc_upload_url(isbn13)
    return ArcUploadUrlOut(upload_url=upload_url, s3_key=s3_key, expires_in=3600)


@router.post("/books/{isbn13}/arc", status_code=204, response_model=None)
async def confirm_arc_upload(
    isbn13: str,
    payload: ArcUploadConfirm,
    db: AsyncSession = Depends(get_db),
    current_user: CurrentUser = Depends(require_publisher),
) -> None:
    """
    Confirm that an ARC file has been uploaded. Enables ARC requests for the title.
    Call this after the presigned PUT completes.
    """
    source = await _require_feed_source(db, current_user)
    book = (await db.execute(select(Book).where(Book.isbn13 == isbn13))).scalar_one_or_none()
    if book is None:
        raise HTTPException(status_code=404, detail="Book not found")

    book.arc_s3_key = payload.s3_key
    book.arc_enabled = True
    await db.commit()


@router.delete("/books/{isbn13}/arc", status_code=204, response_model=None)
async def delete_arc(
    isbn13: str,
    db: AsyncSession = Depends(get_db),
    current_user: CurrentUser = Depends(require_publisher),
) -> None:
    """Remove the ARC file and disable ARC requests for a title."""
    source = await _require_feed_source(db, current_user)
    book = (await db.execute(select(Book).where(Book.isbn13 == isbn13))).scalar_one_or_none()
    if book is None:
        raise HTTPException(status_code=404, detail="Book not found")

    arc_service.delete_arc_from_s3(isbn13)
    book.arc_s3_key = None
    book.arc_enabled = False
    await db.commit()


@router.get("/arcs", response_model=ArcRequestList)
async def list_arc_requests(
    status: str | None = Query(None, regex="^(pending|approved|declined)$"),
    limit: int = Query(50, ge=1, le=200),
    offset: int = Query(0, ge=0),
    db: AsyncSession = Depends(get_db),
    current_user: CurrentUser = Depends(require_publisher),
) -> ArcRequestList:
    """List all ARC requests across the publisher's titles."""
    source = await _require_feed_source(db, current_user)
    requests, total, pending_count = await arc_service.list_arc_requests(
        db, source.id, status=status, limit=limit, offset=offset
    )

    # Enrich with isbn13 + title
    items = []
    for r in requests:
        book = (await db.execute(select(Book).where(Book.id == r.book_id))).scalar_one_or_none()
        items.append(ArcRequestOut(
            id=r.id,
            book_id=r.book_id,
            isbn13=book.isbn13 if book else "",
            title=book.title if book else "",
            requester_type=r.requester_type,
            requester_name=r.requester_name,
            requester_email=r.requester_email,
            requester_company=r.requester_company,
            requester_message=r.requester_message,
            status=r.status,
            decline_reason=r.decline_reason,
            approved_expires_at=r.approved_expires_at,
            reviewed_at=r.reviewed_at,
            created_at=r.created_at,
        ))

    return ArcRequestList(items=items, total=total, pending_count=pending_count)


@router.patch("/arcs/{request_id}", response_model=ArcRequestOut)
async def decide_arc_request(
    request_id: uuid.UUID,
    decision: ArcDecision,
    db: AsyncSession = Depends(get_db),
    current_user: CurrentUser = Depends(require_publisher),
) -> ArcRequestOut:
    """
    Approve or decline an ARC request.
    Declining requires a non-empty reason — this is sent to the requester verbatim.
    """
    source = await _require_feed_source(db, current_user)

    arc = (await db.execute(
        select(ArcRequest).where(
            ArcRequest.id == request_id,
            ArcRequest.feed_source_id == source.id,
        )
    )).scalar_one_or_none()
    if arc is None:
        raise HTTPException(status_code=404, detail="ARC request not found")

    try:
        arc = await arc_service.decide_arc_request(db, arc, decision, current_user.sub)
    except ValueError as e:
        raise HTTPException(status_code=422, detail=str(e))

    book = (await db.execute(select(Book).where(Book.id == arc.book_id))).scalar_one_or_none()
    await db.commit()

    # Send email notification in background
    import asyncio
    publisher_name = source.name
    book_title = book.title if book else "your title"

    if decision.action == "approve" and book and book.arc_s3_key:
        try:
            download_url = arc_service.generate_arc_download_url(book.arc_s3_key)
            asyncio.create_task(send_arc_approved(
                requester_email=arc.requester_email,
                requester_name=arc.requester_name,
                book_title=book_title,
                publisher_name=publisher_name,
                download_url=download_url,
            ))
        except Exception:
            logger.warning("Failed to generate ARC download URL for %s", request_id)
    elif decision.action == "decline":
        asyncio.create_task(send_arc_declined(
            requester_email=arc.requester_email,
            requester_name=arc.requester_name,
            book_title=book_title,
            publisher_name=publisher_name,
            decline_reason=arc.decline_reason or "",
        ))

    return ArcRequestOut(
        id=arc.id,
        book_id=arc.book_id,
        isbn13=book.isbn13 if book else "",
        title=book_title,
        requester_type=arc.requester_type,
        requester_name=arc.requester_name,
        requester_email=arc.requester_email,
        requester_company=arc.requester_company,
        requester_message=arc.requester_message,
        status=arc.status,
        decline_reason=arc.decline_reason,
        approved_expires_at=arc.approved_expires_at,
        reviewed_at=arc.reviewed_at,
        created_at=arc.created_at,
    )


# ── Marketing Asset Hub ────────────────────────────────────────────────────────

from app.models.portal import PublisherAsset

ALLOWED_ASSET_TYPES = {"press_kit", "author_photo", "sell_sheet", "media_pack", "other"}
ALLOWED_CONTENT_TYPES = {
    "application/pdf",
    "image/jpeg",
    "image/png",
    "image/webp",
    "application/zip",
    "application/msword",
    "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
}


@router.get("/books/{isbn13}/assets/upload-url")
async def get_asset_upload_url(
    isbn13: str,
    asset_type: str = Query(...),
    content_type: str = Query(...),
    db: AsyncSession = Depends(get_db),
    current_user: CurrentUser = Depends(require_publisher),
) -> dict:
    """Generate a presigned S3 PUT URL for uploading a marketing asset."""
    if asset_type not in ALLOWED_ASSET_TYPES:
        raise HTTPException(status_code=422, detail=f"asset_type must be one of {sorted(ALLOWED_ASSET_TYPES)}")
    if content_type not in ALLOWED_CONTENT_TYPES:
        raise HTTPException(status_code=422, detail="Unsupported content type")

    source = await _require_feed_source(db, current_user)
    book = (await db.execute(select(Book).where(Book.isbn13 == isbn13))).scalar_one_or_none()
    if book is None:
        raise HTTPException(status_code=404, detail="Book not found")

    settings = get_settings()
    s3_key = f"assets/{isbn13}/{asset_type}/{uuid.uuid4().hex[:8]}"
    s3 = boto3.client("s3", region_name=settings.aws_region)
    upload_url = s3.generate_presigned_url(
        "put_object",
        Params={"Bucket": settings.assets_bucket_name, "Key": s3_key, "ContentType": content_type},
        ExpiresIn=3600,
    )
    return {"upload_url": upload_url, "s3_key": s3_key, "expires_in": 3600}


@router.post("/books/{isbn13}/assets", status_code=201)
async def create_asset(
    isbn13: str,
    payload: dict,
    db: AsyncSession = Depends(get_db),
    current_user: CurrentUser = Depends(require_publisher),
) -> dict:
    """Confirm an asset upload and create the DB record."""
    source = await _require_feed_source(db, current_user)
    book = (await db.execute(select(Book).where(Book.isbn13 == isbn13))).scalar_one_or_none()
    if book is None:
        raise HTTPException(status_code=404, detail="Book not found")

    asset = PublisherAsset(
        id=uuid.uuid4(),
        book_id=book.id,
        feed_source_id=source.id,
        asset_type=payload.get("asset_type", "other"),
        label=payload.get("label", payload.get("original_filename", "Asset")),
        s3_key=payload["s3_key"],
        original_filename=payload.get("original_filename"),
        file_size_bytes=payload.get("file_size_bytes"),
        content_type=payload.get("content_type"),
        public=payload.get("public", True),
    )
    db.add(asset)
    await db.commit()
    await db.refresh(asset)
    return {"id": str(asset.id), "label": asset.label, "asset_type": asset.asset_type}


@router.get("/books/{isbn13}/assets")
async def list_book_assets(
    isbn13: str,
    db: AsyncSession = Depends(get_db),
    current_user: CurrentUser = Depends(require_publisher),
) -> list[dict]:
    """List all marketing assets for a title (publisher view — all assets including private)."""
    source = await _require_feed_source(db, current_user)
    book = (await db.execute(select(Book).where(Book.isbn13 == isbn13))).scalar_one_or_none()
    if book is None:
        raise HTTPException(status_code=404, detail="Book not found")

    assets = (await db.scalars(
        select(PublisherAsset).where(
            PublisherAsset.book_id == book.id,
            PublisherAsset.feed_source_id == source.id,
        ).order_by(PublisherAsset.created_at.desc())
    )).all()

    settings = get_settings()
    s3 = boto3.client("s3", region_name=settings.aws_region)
    result = []
    for a in assets:
        try:
            download_url = s3.generate_presigned_url(
                "get_object",
                Params={"Bucket": settings.assets_bucket_name, "Key": a.s3_key},
                ExpiresIn=3600,
            )
        except Exception:
            download_url = None
        result.append({
            "id": str(a.id),
            "asset_type": a.asset_type,
            "label": a.label,
            "original_filename": a.original_filename,
            "file_size_bytes": a.file_size_bytes,
            "content_type": a.content_type,
            "public": a.public,
            "created_at": a.created_at.isoformat(),
            "download_url": download_url,
        })
    return result


@router.patch("/books/{isbn13}/assets/{asset_id}", status_code=204, response_model=None)
async def update_asset(
    isbn13: str,
    asset_id: uuid.UUID,
    payload: dict,
    db: AsyncSession = Depends(get_db),
    current_user: CurrentUser = Depends(require_publisher),
) -> None:
    """Update asset label or visibility."""
    source = await _require_feed_source(db, current_user)
    asset = (await db.execute(
        select(PublisherAsset).where(
            PublisherAsset.id == asset_id,
            PublisherAsset.feed_source_id == source.id,
        )
    )).scalar_one_or_none()
    if asset is None:
        raise HTTPException(status_code=404, detail="Asset not found")

    if "label" in payload:
        asset.label = payload["label"]
    if "public" in payload:
        asset.public = bool(payload["public"])
    await db.commit()


@router.delete("/books/{isbn13}/assets/{asset_id}", status_code=204, response_model=None)
async def delete_asset(
    isbn13: str,
    asset_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    current_user: CurrentUser = Depends(require_publisher),
) -> None:
    """Delete a marketing asset (removes S3 object and DB record)."""
    source = await _require_feed_source(db, current_user)
    asset = (await db.execute(
        select(PublisherAsset).where(
            PublisherAsset.id == asset_id,
            PublisherAsset.feed_source_id == source.id,
        )
    )).scalar_one_or_none()
    if asset is None:
        raise HTTPException(status_code=404, detail="Asset not found")

    settings = get_settings()
    try:
        boto3.client("s3", region_name=settings.aws_region).delete_object(
            Bucket=settings.assets_bucket_name, Key=asset.s3_key
        )
    except Exception:
        pass

    await db.delete(asset)
    await db.commit()
