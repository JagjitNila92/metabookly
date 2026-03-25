"""Pydantic schemas for the publisher/distributor portal API."""
from __future__ import annotations

import uuid
from datetime import datetime
from typing import Any

from pydantic import BaseModel, ConfigDict


# ─── Feed source ──────────────────────────────────────────────────────────────

class FeedSourceOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    name: str
    source_type: str
    priority: int
    contact_email: str | None
    webhook_url: str | None
    active: bool
    api_key_prefix: str | None
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


class FeedV2Detail(FeedV2Summary):
    sample_errors: list[str] | None


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
