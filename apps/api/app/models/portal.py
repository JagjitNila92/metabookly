"""
Publisher/distributor portal models.

FeedSource      — an entity (publisher, distributor, aggregator) that sends us ONIX feeds
BookEditorialLayer — editorial overrides that survive ONIX re-ingestion
MetadataConflict   — queued conflicts when a feed update touches editorially-modified fields
AiSuggestion       — AI-generated metadata improvements awaiting review
BookMetadataVersion — point-in-time snapshots for rollback
"""
import uuid
from datetime import datetime
from sqlalchemy import Boolean, ForeignKey, Index, Integer, SmallInteger, Text, func
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship
from app.db.base import Base


class FeedSource(Base):
    """
    A publisher, distributor, or bibliographic aggregator that sends us ONIX files.
    Priority determines whose data wins when the same ISBN arrives from multiple sources:
      publisher=30 > distributor=20 > aggregator=10
    """
    __tablename__ = "feed_sources"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    name: Mapped[str] = mapped_column(Text, nullable=False)
    source_type: Mapped[str] = mapped_column(Text, nullable=False)   # publisher | distributor | aggregator
    priority: Mapped[int] = mapped_column(SmallInteger, nullable=False, default=20)

    # Portal login — set when they create a portal account via Cognito
    cognito_sub: Mapped[str | None] = mapped_column(Text, unique=True)

    # API key for automated (non-portal) uploads — stored hashed
    api_key_hash: Mapped[str | None] = mapped_column(Text)
    api_key_prefix: Mapped[str | None] = mapped_column(Text)        # e.g. "mb_sk_abcd" for display

    contact_email: Mapped[str | None] = mapped_column(Text)
    webhook_url: Mapped[str | None] = mapped_column(Text)           # POST feed status here on completion

    # Which distributor this feed source belongs to (set at onboarding).
    # NULL for legacy records. For publisher-uploaded feeds this is still set to
    # the distributor who distributes their titles (e.g. "gardners").
    distributor_code: Mapped[str | None] = mapped_column(Text)
    # "distributor" = distributor uploaded directly; "publisher" = publisher uploading on distributor's behalf
    managed_by: Mapped[str] = mapped_column(Text, nullable=False, default="distributor")

    active: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    created_at: Mapped[datetime] = mapped_column(default=func.now())
    updated_at: Mapped[datetime] = mapped_column(default=func.now(), onupdate=func.now())

    feeds: Mapped[list["OnixFeedV2"]] = relationship("OnixFeedV2", back_populates="feed_source")

    __table_args__ = (
        Index("feed_sources_cognito_sub_idx", "cognito_sub"),
        Index("feed_sources_source_type_idx", "source_type"),
        Index("feed_sources_distributor_code_idx", "distributor_code"),
    )


class OnixFeedV2(Base):
    """
    Extended feed tracking table — replaces onix_feeds for portal submissions.
    Retains onix_feeds for legacy API-based ingestion.
    """
    __tablename__ = "onix_feeds_v2"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    feed_source_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("feed_sources.id", ondelete="SET NULL")
    )

    s3_bucket: Mapped[str] = mapped_column(Text, nullable=False)
    s3_key: Mapped[str] = mapped_column(Text, nullable=False)
    original_filename: Mapped[str | None] = mapped_column(Text)
    file_size_bytes: Mapped[int | None] = mapped_column(Integer)

    # ONIX version detected in the file: "2.1" or "3.0"
    onix_version: Mapped[str | None] = mapped_column(Text)

    # Sequence / delta tracking — publishers may send a sequence number in EDITIONs or custom headers
    sequence_number: Mapped[int | None] = mapped_column(Integer)
    expected_sequence: Mapped[int | None] = mapped_column(Integer)  # what we expected
    gaps_detected: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)

    status: Mapped[str] = mapped_column(Text, nullable=False, default="pending")
    # pending | processing | completed | completed_with_errors | failed

    records_found: Mapped[int | None] = mapped_column(Integer)
    records_upserted: Mapped[int | None] = mapped_column(Integer)
    records_failed: Mapped[int | None] = mapped_column(Integer)
    records_skipped: Mapped[int | None] = mapped_column(Integer)    # lower-priority source
    records_conflicted: Mapped[int | None] = mapped_column(Integer) # editorial layer conflicts
    error_detail: Mapped[str | None] = mapped_column(Text)
    sample_errors: Mapped[list | None] = mapped_column(JSONB)       # up to 20 sample error messages

    triggered_by: Mapped[str | None] = mapped_column(Text)         # portal | api_key | s3_event | admin
    started_at: Mapped[datetime | None] = mapped_column()
    completed_at: Mapped[datetime | None] = mapped_column()
    created_at: Mapped[datetime] = mapped_column(default=func.now())

    feed_source: Mapped["FeedSource | None"] = relationship("FeedSource", back_populates="feeds")

    __table_args__ = (
        Index("onix_feeds_v2_feed_source_idx", "feed_source_id"),
        Index("onix_feeds_v2_status_idx", "status"),
        Index("onix_feeds_v2_created_idx", "created_at"),
    )


class BookEditorialLayer(Base):
    """
    Editorial fields that can be modified in the portal and survive ONIX re-ingestion.
    One row per book — ONIX-locked fields stay on the Book model itself.
    """
    __tablename__ = "book_editorial_layers"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    book_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("books.id", ondelete="CASCADE"), nullable=False, unique=True
    )

    # Editable fields — None means "use the ONIX value"
    description: Mapped[str | None] = mapped_column(Text)
    toc: Mapped[str | None] = mapped_column(Text)
    excerpt: Mapped[str | None] = mapped_column(Text)

    # Additional subject headings beyond what the publisher sent
    extra_subjects: Mapped[list | None] = mapped_column(JSONB)      # [{scheme_id, subject_code, heading}]

    # Per-field source tracking — tells us which fields have been editorially modified
    # e.g. {"description": "editorial", "toc": "onix", "excerpt": "ai_accepted"}
    field_sources: Mapped[dict | None] = mapped_column(JSONB)

    edited_by: Mapped[str | None] = mapped_column(Text)            # Cognito sub of last editor
    created_at: Mapped[datetime] = mapped_column(default=func.now())
    updated_at: Mapped[datetime] = mapped_column(default=func.now(), onupdate=func.now())

    __table_args__ = (
        Index("book_editorial_layers_book_id_idx", "book_id"),
    )


class MetadataConflict(Base):
    """
    Raised when an incoming ONIX feed tries to update a field that has been
    editorially modified. The update is queued here instead of being auto-applied.
    """
    __tablename__ = "metadata_conflicts"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    book_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("books.id", ondelete="CASCADE"), nullable=False
    )
    feed_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("onix_feeds_v2.id", ondelete="SET NULL")
    )

    field_name: Mapped[str] = mapped_column(Text, nullable=False)   # e.g. "description"
    onix_value: Mapped[str | None] = mapped_column(Text)            # the value the feed wants to set
    editorial_value: Mapped[str | None] = mapped_column(Text)       # the current editorial value

    status: Mapped[str] = mapped_column(Text, nullable=False, default="pending")
    # pending | accepted_onix | kept_editorial

    resolved_by: Mapped[str | None] = mapped_column(Text)           # Cognito sub
    resolved_at: Mapped[datetime | None] = mapped_column()
    created_at: Mapped[datetime] = mapped_column(default=func.now())

    __table_args__ = (
        Index("metadata_conflicts_book_id_idx", "book_id"),
        Index("metadata_conflicts_status_idx", "status"),
    )


class AiSuggestion(Base):
    """
    An AI-generated improvement to a book's metadata.
    High-confidence suggestions are auto-accepted; medium/low go through review.
    """
    __tablename__ = "ai_suggestions"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    book_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("books.id", ondelete="CASCADE"), nullable=False
    )

    field_name: Mapped[str] = mapped_column(Text, nullable=False)   # e.g. "description", "subject_heading"
    original_value: Mapped[str | None] = mapped_column(Text)
    suggested_value: Mapped[str] = mapped_column(Text, nullable=False)

    confidence: Mapped[str] = mapped_column(Text, nullable=False)   # high | medium | low
    model_id: Mapped[str | None] = mapped_column(Text)              # e.g. "anthropic.claude-3-haiku-..."
    reasoning: Mapped[str | None] = mapped_column(Text)             # brief explanation shown in UI

    status: Mapped[str] = mapped_column(Text, nullable=False, default="pending")
    # pending | accepted | rejected | auto_accepted

    reviewed_by: Mapped[str | None] = mapped_column(Text)           # Cognito sub, None if auto-accepted
    reviewed_at: Mapped[datetime | None] = mapped_column()
    created_at: Mapped[datetime] = mapped_column(default=func.now())

    __table_args__ = (
        Index("ai_suggestions_book_id_idx", "book_id"),
        Index("ai_suggestions_status_confidence_idx", "status", "confidence"),
    )


class BookMetadataVersion(Base):
    """
    Point-in-time snapshot of a book record for audit trail and rollback.
    Written on every significant change (ONIX ingest, editorial edit, AI accept).
    """
    __tablename__ = "book_metadata_versions"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    book_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("books.id", ondelete="CASCADE"), nullable=False
    )
    version_number: Mapped[int] = mapped_column(Integer, nullable=False)

    # Who/what caused this version:
    # "onix:{feed_id}", "editorial:{user_sub}", "ai:{suggestion_id}"
    changed_by: Mapped[str] = mapped_column(Text, nullable=False)

    # Full book snapshot including editorial layer at time of change
    snapshot: Mapped[dict] = mapped_column(JSONB, nullable=False)

    created_at: Mapped[datetime] = mapped_column(default=func.now())

    __table_args__ = (
        Index("book_metadata_versions_book_id_idx", "book_id"),
        Index("book_metadata_versions_book_version_idx", "book_id", "version_number", unique=True),
    )


class BookDistributor(Base):
    """
    Which distributor carries which title — populated on every ONIX ingest.
    A title can be carried by multiple distributors (e.g. Gardners and Bertrams).
    This is the routing table for future order placement.
    """
    __tablename__ = "book_distributors"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    book_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("books.id", ondelete="CASCADE"), nullable=False
    )
    distributor_code: Mapped[str] = mapped_column(Text, nullable=False)
    feed_source_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("feed_sources.id", ondelete="SET NULL")
    )
    created_at: Mapped[datetime] = mapped_column(default=func.now())

    __table_args__ = (
        Index("book_distributors_book_id_idx", "book_id"),
        Index("book_distributors_distributor_code_idx", "distributor_code"),
    )


class SearchEvent(Base):
    """Logged whenever a catalog search is performed — retailer or anonymous."""
    __tablename__ = "search_events"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    retailer_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("retailers.id", ondelete="SET NULL")
    )
    query: Mapped[str | None] = mapped_column(Text)
    filters: Mapped[dict | None] = mapped_column(JSONB)   # active filter values
    result_count: Mapped[int | None] = mapped_column(Integer)
    is_anonymous: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    created_at: Mapped[datetime] = mapped_column(default=func.now())

    __table_args__ = (
        Index("search_events_retailer_id_idx", "retailer_id"),
        Index("search_events_created_at_idx", "created_at"),
    )


class BookViewEvent(Base):
    """Logged whenever a book detail page is opened."""
    __tablename__ = "book_view_events"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    retailer_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("retailers.id", ondelete="SET NULL")
    )
    book_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("books.id", ondelete="CASCADE"), nullable=False
    )
    isbn13: Mapped[str] = mapped_column(Text, nullable=False)
    is_anonymous: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    created_at: Mapped[datetime] = mapped_column(default=func.now())

    __table_args__ = (
        Index("book_view_events_book_id_idx", "book_id"),
        Index("book_view_events_retailer_id_idx", "retailer_id"),
        Index("book_view_events_created_at_idx", "created_at"),
    )


class PriceCheckEvent(Base):
    """
    Logged whenever a retailer checks pricing for a title.
    distributors_queried — all distributor codes fanned out to
    distributors_with_price — codes that returned a price
    had_gap — True when queried > 0 distributors but none returned a price
    """
    __tablename__ = "price_check_events"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    retailer_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("retailers.id", ondelete="SET NULL")
    )
    book_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("books.id", ondelete="CASCADE"), nullable=False
    )
    isbn13: Mapped[str] = mapped_column(Text, nullable=False)
    distributors_queried: Mapped[list] = mapped_column(JSONB, nullable=False)
    distributors_with_price: Mapped[list] = mapped_column(JSONB, nullable=False)
    had_gap: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    created_at: Mapped[datetime] = mapped_column(default=func.now())

    __table_args__ = (
        Index("price_check_events_book_id_idx", "book_id"),
        Index("price_check_events_retailer_id_idx", "retailer_id"),
        Index("price_check_events_created_at_idx", "created_at"),
        Index("price_check_events_had_gap_idx", "had_gap"),
    )
