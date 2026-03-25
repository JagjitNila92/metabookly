from datetime import datetime
from uuid import UUID
from pydantic import BaseModel


class DistributorOption(BaseModel):
    distributor_code: str
    distributor_name: str
    requires_account_number: bool


class LinkedAccountOut(BaseModel):
    id: UUID
    distributor_code: str
    distributor_name: str
    account_number: str | None
    status: str  # pending | approved | rejected | withdrawn
    rejection_reason: str | None
    created_at: datetime

    model_config = {"from_attributes": True}


class RetailerProfileOut(BaseModel):
    id: UUID
    company_name: str
    email: str
    country_code: str
    san: str | None
    accounts: list[LinkedAccountOut]

    model_config = {"from_attributes": True}


class LinkAccountRequest(BaseModel):
    distributor_code: str
    account_number: str | None = None


class UpdateProfileRequest(BaseModel):
    company_name: str | None = None
    country_code: str | None = None
    san: str | None = None


# ── Distributor-facing schemas ─────────────────────────────────────────────────

class RetailerSummary(BaseModel):
    id: UUID
    company_name: str
    email: str

    model_config = {"from_attributes": True}


class AccountRequestOut(BaseModel):
    id: UUID
    distributor_code: str
    distributor_name: str
    account_number: str | None
    status: str
    rejection_reason: str | None
    retailer: RetailerSummary
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


class ReviewRequest(BaseModel):
    rejection_reason: str | None = None
