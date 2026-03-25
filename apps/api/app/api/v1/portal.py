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

import logging
import uuid
from datetime import datetime, UTC

from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException, Query, status
from sqlalchemy import func, select
from sqlalchemy.dialects.postgresql import insert as pg_insert
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_current_user, get_db, require_publisher
from app.auth.models import CurrentUser
from app.aws.s3 import download_from_s3, generate_onix_upload_url
from app.config import get_settings
from app.models.book import Book
from app.models.portal import (
    AiSuggestion,
    BookEditorialLayer,
    FeedSource,
    MetadataConflict,
    OnixFeedV2,
)
from app.schemas.portal import (
    AiSuggestionListResponse,
    AiSuggestionOut,
    BulkAcceptRequest,
    BulkAcceptResponse,
    ConflictListResponse,
    ConflictOut,
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
