import uuid
from datetime import datetime
from sqlalchemy import Boolean, Text, func
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship
from app.db.base import Base


class Retailer(Base):
    __tablename__ = "retailers"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    cognito_sub: Mapped[str] = mapped_column(Text, nullable=False, unique=True)
    company_name: Mapped[str] = mapped_column(Text, nullable=False)
    san: Mapped[str | None] = mapped_column(Text)
    email: Mapped[str] = mapped_column(Text, nullable=False, unique=True)
    country_code: Mapped[str] = mapped_column(Text, nullable=False, default="GB")
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
        UUID(as_uuid=True), nullable=False
    )
    distributor_code: Mapped[str] = mapped_column(Text, nullable=False)
    account_number: Mapped[str | None] = mapped_column(Text)
    active: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    created_at: Mapped[datetime] = mapped_column(default=func.now())

    retailer: Mapped["Retailer"] = relationship("Retailer", back_populates="distributor_accounts")
