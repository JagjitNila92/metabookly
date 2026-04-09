"""
Feature flag models.

GlobalFeatureFlag   — platform-wide switches (ordering_enabled, ai_suggestions, …)
AccountFeatureFlag  — per-account overrides that shadow the global value
DistributorAccount  — portal login record for distributor staff
"""
import uuid
from datetime import datetime
from sqlalchemy import Boolean, ForeignKey, Text, UniqueConstraint, func
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base


class GlobalFeatureFlag(Base):
    __tablename__ = "global_feature_flags"

    flag_name: Mapped[str] = mapped_column(Text, primary_key=True)
    enabled: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    description: Mapped[str | None] = mapped_column(Text)
    updated_at: Mapped[datetime] = mapped_column(default=func.now(), onupdate=func.now())
    updated_by: Mapped[str | None] = mapped_column(Text)


class AccountFeatureFlag(Base):
    __tablename__ = "account_feature_flags"
    __table_args__ = (
        UniqueConstraint("account_type", "account_id", "flag_name", name="uq_account_feature_flags"),
    )

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    # retailer | publisher | distributor
    account_type: Mapped[str] = mapped_column(Text, nullable=False)
    account_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), nullable=False)
    flag_name: Mapped[str] = mapped_column(Text, nullable=False)
    enabled: Mapped[bool] = mapped_column(Boolean, nullable=False)
    updated_at: Mapped[datetime] = mapped_column(default=func.now(), onupdate=func.now())
    updated_by: Mapped[str | None] = mapped_column(Text)


class DistributorAccount(Base):
    """Portal login record for a distributor staff member."""
    __tablename__ = "distributor_accounts"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    cognito_sub: Mapped[str] = mapped_column(Text, nullable=False, unique=True)
    distributor_code: Mapped[str] = mapped_column(
        Text,
        ForeignKey("distributor_settings.distributor_code", ondelete="CASCADE"),
        nullable=False,
    )
    company_name: Mapped[str] = mapped_column(Text, nullable=False)
    email: Mapped[str] = mapped_column(Text, nullable=False, unique=True)
    contact_name: Mapped[str | None] = mapped_column(Text)
    active: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    created_at: Mapped[datetime] = mapped_column(default=func.now())
    updated_at: Mapped[datetime] = mapped_column(default=func.now(), onupdate=func.now())
