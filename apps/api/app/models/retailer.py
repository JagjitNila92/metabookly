import uuid
from datetime import datetime
from sqlalchemy import Boolean, ForeignKey, Integer, Text, func
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship
from app.db.base import Base

# Max seats per plan (used by service layer — not stored in DB)
PLAN_MAX_SEATS: dict[str, int | None] = {
    "free": 1,
    "starter_api": 3,
    "intelligence": 10,
    "enterprise": None,  # unlimited
}

# Status lifecycle: pending → approved | rejected
# A retailer can withdraw a pending/rejected request (status → withdrawn).
ACCOUNT_STATUSES = ("pending", "approved", "rejected", "withdrawn")


class Retailer(Base):
    __tablename__ = "retailers"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    cognito_sub: Mapped[str] = mapped_column(Text, nullable=False, unique=True)
    company_name: Mapped[str] = mapped_column(Text, nullable=False)
    san: Mapped[str | None] = mapped_column(Text)
    email: Mapped[str] = mapped_column(Text, nullable=False, unique=True)
    country_code: Mapped[str] = mapped_column(Text, nullable=False, default="GB")
    contact_name: Mapped[str | None] = mapped_column(Text)
    phone: Mapped[str | None] = mapped_column(Text)
    role: Mapped[str | None] = mapped_column(Text)
    referral_source: Mapped[str | None] = mapped_column(Text)
    # Plan tier: free | starter_api | intelligence | enterprise
    plan: Mapped[str] = mapped_column(Text, nullable=False, default="free")
    plan_activated_at: Mapped[datetime | None] = mapped_column(nullable=True)
    plan_expires_at: Mapped[datetime | None] = mapped_column(nullable=True)
    # Extra seats purchased on top of plan default (billed via Stripe)
    extra_seats: Mapped[int] = mapped_column(Integer, nullable=False, default=0)

    active: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    created_at: Mapped[datetime] = mapped_column(default=func.now())
    updated_at: Mapped[datetime] = mapped_column(default=func.now(), onupdate=func.now())

    distributor_accounts: Mapped[list["RetailerDistributor"]] = relationship(
        "RetailerDistributor", back_populates="retailer", cascade="all, delete-orphan"
    )


class RetailerDistributor(Base):
    __tablename__ = "retailer_distributors"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    retailer_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("retailers.id", ondelete="CASCADE"), nullable=False
    )
    distributor_code: Mapped[str] = mapped_column(Text, nullable=False)
    account_number: Mapped[str | None] = mapped_column(Text)
    # pending → approved | rejected; retailer can withdraw pending/rejected requests
    status: Mapped[str] = mapped_column(Text, nullable=False, default="pending")
    rejection_reason: Mapped[str | None] = mapped_column(Text)
    # Set by admin on approval — allows retailer to place gratis (FOC) orders via this distributor
    gratis_enabled: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    created_at: Mapped[datetime] = mapped_column(default=func.now())
    updated_at: Mapped[datetime] = mapped_column(default=func.now(), onupdate=func.now())

    retailer: Mapped["Retailer"] = relationship("Retailer", back_populates="distributor_accounts")
