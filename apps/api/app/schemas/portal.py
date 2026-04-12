"""Pydantic schemas for the publisher/distributor portal API."""
from __future__ import annotations

import uuid
from datetime import datetime
from typing import Any

from pydantic import BaseModel, ConfigDict


# ─── Publisher registration ───────────────────────────────────────────────────

class PublisherRegisterRequest(BaseModel):
    email: str
    password: str
    contact_name: str
    company_name: str
    publisher_type: str | None = None   # indie | traditional | self-pub | university-press
    phone: str | None = None
    website: str | None = None
    title_count: str | None = None      # approx range e.g. "1-10", "11-50", "51-200", "200+"
    referral_source: str | None = None


# ─── Feed source ──────────────────────────────────────────────────────────────

class FeedSourceOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    name: str
    source_type: str
    priority: int
    plan: str
    contact_email: str | None
    contact_name: str | None
    webhook_url: str | None
    active: bool
    api_key_prefix: str | None
    created_at: datetime


# ─── API keys ─────────────────────────────────────────────────────────────────

class ApiKeyOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    key_prefix: str
    label: str | None
    created_at: datetime
    last_used_at: datetime | None


class ApiKeyCreated(ApiKeyOut):
    """Returned once at creation — includes plaintext key. Not stored server-side."""
    plaintext_key: str


class CreateApiKeyRequest(BaseModel):
    label: str | None = None   # optional name e.g. "CI pipeline"


# ─── Book detail (combined ONIX + editorial layer) ────────────────────────────

class BookDetailOut(BaseModel):
    """
    Full book record combining ONIX-sourced fields with any editorial overrides.
    field_sources shows the origin of each editable field:
      "onix"        — came from the ONIX feed, no manual override
      "editorial"   — manually set in the portal
      "ai_accepted" — AI suggestion that was accepted
    """
    isbn13: str
    isbn10: str | None
    title: str
    subtitle: str | None
    product_form: str | None
    page_count: int | None
    publication_date: str | None    # ISO date string or None
    publishing_status: str | None
    uk_rights: bool | None
    rrp_gbp: str | None
    rrp_usd: str | None
    cover_image_url: str | None
    height_mm: int | None
    width_mm: int | None
    metadata_score: int | None

    # Editable fields — effective value (editorial override takes priority over ONIX)
    description: str | None
    toc: str | None
    excerpt: str | None

    # Per-field source: which fields have been manually overridden
    field_sources: dict[str, Any]

    # ONIX original values (so UI can show "what ONIX says" vs "what's live")
    onix_description: str | None
    onix_toc: str | None
    onix_excerpt: str | None


# ─── Version history ──────────────────────────────────────────────────────────

class BookVersionOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    version_number: int
    changed_by: str
    snapshot: dict[str, Any]
    created_at: datetime


# ─── Upload URL ───────────────────────────────────────────────────────────────

class UploadUrlResponse(BaseModel):
    feed_id: uuid.UUID
    upload_url: str          # pre-signed S3 PUT URL
    s3_key: str
    expires_in_seconds: int  # how long the URL is valid


# ─── Feed records ─────────────────────────────────────────────────────────────

class FeedV2Summary(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    original_filename: str | None
    file_size_bytes: int | None
    onix_version: str | None
    sequence_number: int | None
    gaps_detected: bool
    status: str
    records_found: int | None
    records_upserted: int | None
    records_failed: int | None
    records_skipped: int | None
    records_conflicted: int | None
    error_detail: str | None
    triggered_by: str | None
    started_at: datetime | None
    completed_at: datetime | None
    created_at: datetime
    validation_passed: bool | None
    validation_errors_count: int | None
    validation_warnings_count: int | None


class FeedV2Detail(FeedV2Summary):
    sample_errors: list[Any] | None        # ingest errors (strings)
    validation_errors: list[Any] | None    # structured [{isbn13,field,message,line,severity}]


class FeedV2ListResponse(BaseModel):
    feeds: list[FeedV2Summary]
    total: int


class TriggerIngestResponse(BaseModel):
    feed_id: uuid.UUID
    status: str
    onix_version: str | None = None
    gaps_detected: bool = False
    records_found: int = 0
    records_upserted: int = 0
    records_failed: int = 0
    records_skipped: int = 0
    records_conflicted: int = 0
    errors: list[str] = []


# ─── Conflicts ────────────────────────────────────────────────────────────────

class ConflictOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    book_id: uuid.UUID
    feed_id: uuid.UUID | None
    field_name: str
    onix_value: str | None
    editorial_value: str | None
    status: str
    resolved_by: str | None
    resolved_at: datetime | None
    created_at: datetime


class ConflictListResponse(BaseModel):
    conflicts: list[ConflictOut]
    total: int


class ResolveConflictRequest(BaseModel):
    resolution: str  # "accept_onix" | "keep_editorial"


# ─── Editorial layer ──────────────────────────────────────────────────────────

class EditorialLayerOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    book_id: uuid.UUID
    description: str | None
    toc: str | None
    excerpt: str | None
    extra_subjects: list[dict] | None
    field_sources: dict[str, str] | None
    edited_by: str | None
    updated_at: datetime


class EditorialLayerUpdate(BaseModel):
    description: str | None = None
    toc: str | None = None
    excerpt: str | None = None
    extra_subjects: list[dict] | None = None


# ─── AI suggestions ───────────────────────────────────────────────────────────

class AiSuggestionOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    book_id: uuid.UUID
    field_name: str
    original_value: str | None
    suggested_value: str
    confidence: str
    reasoning: str | None
    status: str
    reviewed_by: str | None
    reviewed_at: datetime | None
    created_at: datetime


class AiSuggestionListResponse(BaseModel):
    suggestions: list[AiSuggestionOut]
    total: int
    by_confidence: dict[str, int]   # {"high": 3, "medium": 12, "low": 5}


class BulkAcceptRequest(BaseModel):
    confidence: str | None = None   # if set, accept all pending of this confidence
    ids: list[uuid.UUID] | None = None  # explicit list of suggestion IDs


class BulkAcceptResponse(BaseModel):
    accepted: int
    rejected: int
