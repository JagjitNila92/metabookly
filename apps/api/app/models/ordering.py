import uuid
from datetime import date, datetime
from decimal import Decimal
from sqlalchemy import Boolean, Date, ForeignKey, Integer, Numeric, Text, func
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship
from app.db.base import Base


class RetailerSettings(Base):
    __tablename__ = "retailer_settings"

    retailer_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("retailers.id", ondelete="CASCADE"), primary_key=True,
    )
    notify_order_submitted: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    notify_backorder_alert: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    notify_invoice_available: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    updated_at: Mapped[datetime] = mapped_column(default=func.now(), onupdate=func.now())


class RetailerAddress(Base):
    __tablename__ = "retailer_addresses"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    retailer_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("retailers.id", ondelete="CASCADE"), nullable=False,
    )
    address_type: Mapped[str] = mapped_column(Text, nullable=False)   # 'billing' | 'delivery'
    label: Mapped[str] = mapped_column(Text, nullable=False)
    contact_name: Mapped[str] = mapped_column(Text, nullable=False)
    line1: Mapped[str] = mapped_column(Text, nullable=False)
    line2: Mapped[str | None] = mapped_column(Text)
    city: Mapped[str] = mapped_column(Text, nullable=False)
    county: Mapped[str | None] = mapped_column(Text)
    postcode: Mapped[str] = mapped_column(Text, nullable=False)
    country_code: Mapped[str] = mapped_column(Text, nullable=False, default="GB")
    is_default: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    created_at: Mapped[datetime] = mapped_column(default=func.now())
    updated_at: Mapped[datetime] = mapped_column(default=func.now(), onupdate=func.now())


class DistributorSettings(Base):
    __tablename__ = "distributor_settings"

    distributor_code: Mapped[str] = mapped_column(Text, primary_key=True)
    allows_dropship: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    min_order_value_gbp: Mapped[Decimal | None] = mapped_column(Numeric(8, 2))
    updated_at: Mapped[datetime] = mapped_column(default=func.now(), onupdate=func.now())


class Order(Base):
    __tablename__ = "orders"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    retailer_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("retailers.id", ondelete="RESTRICT"), nullable=False,
    )
    po_number: Mapped[str] = mapped_column(Text, nullable=False, unique=True)
    status: Mapped[str] = mapped_column(Text, nullable=False, default="draft")
    billing_address_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("retailer_addresses.id", ondelete="SET NULL"),
    )
    delivery_address_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("retailer_addresses.id", ondelete="SET NULL"),
    )
    delivery_address_snapshot: Mapped[dict | None] = mapped_column(JSONB)
    delivery_type: Mapped[str] = mapped_column(Text, nullable=False, default="stock")
    total_lines: Mapped[int | None] = mapped_column(Integer)
    total_gbp: Mapped[Decimal | None] = mapped_column(Numeric(10, 2))
    submitted_at: Mapped[datetime | None] = mapped_column()
    created_at: Mapped[datetime] = mapped_column(default=func.now())
    updated_at: Mapped[datetime] = mapped_column(default=func.now(), onupdate=func.now())

    lines: Mapped[list["OrderLine"]] = relationship(
        "OrderLine", back_populates="order", cascade="all, delete-orphan",
        order_by="OrderLine.created_at",
    )


class OrderLine(Base):
    __tablename__ = "order_lines"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    order_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("orders.id", ondelete="CASCADE"), nullable=False,
    )
    distributor_code: Mapped[str] = mapped_column(Text, nullable=False)
    delivery_type: Mapped[str] = mapped_column(Text, nullable=False, default="stock")
    status: Mapped[str] = mapped_column(Text, nullable=False, default="pending")
    transmission_attempts: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    last_attempted_at: Mapped[datetime | None] = mapped_column()
    external_po_ref: Mapped[str | None] = mapped_column(Text)
    despatch_note_ref: Mapped[str | None] = mapped_column(Text)
    tracking_ref: Mapped[str | None] = mapped_column(Text)
    estimated_delivery_date: Mapped[date | None] = mapped_column(Date)
    subtotal_gbp: Mapped[Decimal | None] = mapped_column(Numeric(10, 2))
    created_at: Mapped[datetime] = mapped_column(default=func.now())
    updated_at: Mapped[datetime] = mapped_column(default=func.now(), onupdate=func.now())

    order: Mapped["Order"] = relationship("Order", back_populates="lines")
    items: Mapped[list["OrderLineItem"]] = relationship(
        "OrderLineItem", back_populates="line", cascade="all, delete-orphan",
        order_by="OrderLineItem.created_at",
    )
    invoice: Mapped["Invoice | None"] = relationship(
        "Invoice", back_populates="order_line", uselist=False,
    )


class OrderLineItem(Base):
    __tablename__ = "order_line_items"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    order_line_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("order_lines.id", ondelete="CASCADE"), nullable=False,
    )
    book_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("books.id", ondelete="RESTRICT"), nullable=False,
    )
    isbn13: Mapped[str] = mapped_column(Text, nullable=False)
    retailer_line_ref: Mapped[str] = mapped_column(Text, nullable=False)
    quantity_ordered: Mapped[int] = mapped_column(Integer, nullable=False)
    quantity_confirmed: Mapped[int | None] = mapped_column(Integer)
    quantity_despatched: Mapped[int | None] = mapped_column(Integer)
    quantity_invoiced: Mapped[int | None] = mapped_column(Integer)
    status: Mapped[str] = mapped_column(Text, nullable=False, default="pending")
    expected_despatch_date: Mapped[date | None] = mapped_column(Date)
    trade_price_gbp: Mapped[Decimal | None] = mapped_column(Numeric(10, 2))
    rrp_gbp: Mapped[Decimal | None] = mapped_column(Numeric(10, 2))
    created_at: Mapped[datetime] = mapped_column(default=func.now())
    updated_at: Mapped[datetime] = mapped_column(default=func.now(), onupdate=func.now())

    line: Mapped["OrderLine"] = relationship("OrderLine", back_populates="items")


class Invoice(Base):
    __tablename__ = "invoices"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    order_line_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("order_lines.id", ondelete="CASCADE"),
        nullable=False, unique=True,
    )
    invoice_number: Mapped[str] = mapped_column(Text, nullable=False)
    invoice_date: Mapped[date] = mapped_column(Date, nullable=False)
    net_gbp: Mapped[Decimal] = mapped_column(Numeric(10, 2), nullable=False)
    vat_gbp: Mapped[Decimal] = mapped_column(Numeric(10, 2), nullable=False, default=Decimal("0"))
    gross_gbp: Mapped[Decimal] = mapped_column(Numeric(10, 2), nullable=False)
    raw_edi: Mapped[str | None] = mapped_column(Text)
    created_at: Mapped[datetime] = mapped_column(default=func.now())

    order_line: Mapped["OrderLine"] = relationship("OrderLine", back_populates="invoice")
