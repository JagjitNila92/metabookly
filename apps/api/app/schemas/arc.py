"""Schemas for ARC (Advance Reading Copy) requests."""
import uuid
from datetime import datetime
from typing import Literal
from pydantic import BaseModel, EmailStr


# ── Inbound ────────────────────────────────────────────────────────────────────

class ArcRequestCreate(BaseModel):
    """Submitted by anyone requesting an ARC of a title."""
    requester_type: Literal["retailer", "trade_press", "blogger", "other"]
    requester_name: str
    requester_email: EmailStr
    requester_company: str | None = None
    requester_message: str | None = None


class ArcDecision(BaseModel):
    """Publisher approves or declines an ARC request. Decline requires a reason."""
    action: Literal["approve", "decline"]
    decline_reason: str | None = None  # required when action="decline"


class ArcUploadConfirm(BaseModel):
    """Publisher confirms that ARC file has been uploaded to the presigned URL."""
    s3_key: str
    original_filename: str


# ── Outbound ───────────────────────────────────────────────────────────────────

class ArcRequestOut(BaseModel):
    id: uuid.UUID
    book_id: uuid.UUID
    isbn13: str
    title: str
    requester_type: str
    requester_name: str
    requester_email: str
    requester_company: str | None
    requester_message: str | None
    status: str   # pending | approved | declined
    decline_reason: str | None
    approved_expires_at: datetime | None
    reviewed_at: datetime | None
    created_at: datetime

    model_config = {"from_attributes": True}


class ArcRequestList(BaseModel):
    items: list[ArcRequestOut]
    total: int
    pending_count: int


class ArcUploadUrlOut(BaseModel):
    upload_url: str
    s3_key: str
    expires_in: int


class ArcStatusOut(BaseModel):
    """Returned to retailers checking whether they already have a request in flight."""
    has_request: bool
    status: str | None        # pending | approved | declined | None
    decline_reason: str | None
    download_url: str | None  # presigned GET URL if approved and not expired
