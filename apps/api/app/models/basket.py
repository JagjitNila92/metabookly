import uuid
from datetime import datetime
from sqlalchemy import ForeignKey, Integer, Text, func
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship
from app.db.base import Base


class Basket(Base):
    __tablename__ = "baskets"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    retailer_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("retailers.id", ondelete="CASCADE"),
        nullable=False, unique=True,
    )
    created_at: Mapped[datetime] = mapped_column(default=func.now())
    updated_at: Mapped[datetime] = mapped_column(default=func.now(), onupdate=func.now())

    items: Mapped[list["BasketItem"]] = relationship(
        "BasketItem", back_populates="basket", cascade="all, delete-orphan",
        order_by="BasketItem.added_at",
    )


class BasketItem(Base):
    __tablename__ = "basket_items"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    basket_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("baskets.id", ondelete="CASCADE"), nullable=False,
    )
    book_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("books.id", ondelete="CASCADE"), nullable=False,
    )
    isbn13: Mapped[str] = mapped_column(Text, nullable=False)
    quantity: Mapped[int] = mapped_column(Integer, nullable=False)
    preferred_distributor_code: Mapped[str | None] = mapped_column(Text)
    added_at: Mapped[datetime] = mapped_column(default=func.now())

    basket: Mapped["Basket"] = relationship("Basket", back_populates="items")
