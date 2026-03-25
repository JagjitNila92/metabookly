"""Schemas for basket, orders, retailer settings, addresses, and invoices."""
from datetime import date, datetime
from decimal import Decimal
from uuid import UUID

from pydantic import BaseModel, Field, model_validator


# ─── Addresses ────────────────────────────────────────────────────────────────

class AddressIn(BaseModel):
    """Inline one-off delivery address (not saved to address book)."""
    contact_name: str
    line1: str
    line2: str | None = None
    city: str
    county: str | None = None
    postcode: str
    country_code: str = "GB"


class AddressCreate(BaseModel):
    address_type: str = Field(pattern="^(billing|delivery)$")
    label: str
    contact_name: str
    line1: str
    line2: str | None = None
    city: str
    county: str | None = None
    postcode: str
    country_code: str = "GB"
    is_default: bool = False


class AddressUpdate(BaseModel):
    label: str | None = None
    contact_name: str | None = None
    line1: str | None = None
    line2: str | None = None
    city: str | None = None
    county: str | None = None
    postcode: str | None = None
    country_code: str | None = None
    is_default: bool | None = None


class AddressOut(BaseModel):
    id: UUID
    address_type: str
    label: str
    contact_name: str
    line1: str
    line2: str | None
    city: str
    county: str | None
    postcode: str
    country_code: str
    is_default: bool
    created_at: datetime

    model_config = {"from_attributes": True}


# ─── Retailer settings ────────────────────────────────────────────────────────

class RetailerSettingsOut(BaseModel):
    notify_order_submitted: bool
    notify_backorder_alert: bool
    notify_invoice_available: bool

    model_config = {"from_attributes": True}


class RetailerSettingsUpdate(BaseModel):
    notify_order_submitted: bool | None = None
    notify_backorder_alert: bool | None = None
    notify_invoice_available: bool | None = None


# ─── Basket ───────────────────────────────────────────────────────────────────

class BasketItemAdd(BaseModel):
    isbn13: str = Field(min_length=13, max_length=13)
    quantity: int = Field(ge=1)
    preferred_distributor_code: str | None = None


class BasketItemUpdate(BaseModel):
    quantity: int | None = Field(default=None, ge=1)
    preferred_distributor_code: str | None = None


class RoutedItemOut(BaseModel):
    """A basket item enriched with routing and pricing information."""
    isbn13: str
    title: str
    cover_image_url: str | None
    quantity: int
    preferred_distributor_code: str | None
    routed_distributor_code: str | None       # None if no active account can supply
    trade_price_gbp: Decimal | None
    rrp_gbp: Decimal | None
    margin_pct: Decimal | None                # (rrp - trade) / rrp * 100


class BasketOut(BaseModel):
    item_count: int
    total_cost_gbp: Decimal | None
    avg_margin_pct: Decimal | None
    items: list[RoutedItemOut]


# ─── Orders ───────────────────────────────────────────────────────────────────

class OrderLineItemOut(BaseModel):
    id: UUID
    isbn13: str
    title: str | None = None
    quantity_ordered: int
    quantity_confirmed: int | None
    quantity_despatched: int | None
    quantity_invoiced: int | None
    status: str
    expected_despatch_date: date | None
    trade_price_gbp: Decimal | None
    rrp_gbp: Decimal | None

    model_config = {"from_attributes": True}


class OrderLineOut(BaseModel):
    id: UUID
    distributor_code: str
    status: str
    transmission_attempts: int
    external_po_ref: str | None
    tracking_ref: str | None
    estimated_delivery_date: date | None
    subtotal_gbp: Decimal | None
    items: list[OrderLineItemOut]

    model_config = {"from_attributes": True}


class OrderOut(BaseModel):
    id: UUID
    po_number: str
    status: str
    delivery_type: str
    total_lines: int | None
    total_gbp: Decimal | None
    submitted_at: datetime | None
    created_at: datetime
    lines: list[OrderLineOut]

    model_config = {"from_attributes": True}


class OrderSummaryOut(BaseModel):
    """Lightweight order list item — no line details."""
    id: UUID
    po_number: str
    status: str
    total_lines: int | None
    total_gbp: Decimal | None
    submitted_at: datetime | None
    created_at: datetime

    model_config = {"from_attributes": True}


class BackorderLineOut(BaseModel):
    """A single back-ordered item across all orders."""
    order_id: UUID
    order_line_id: UUID
    item_id: UUID
    po_number: str
    distributor_code: str
    isbn13: str
    title: str | None = None
    quantity_ordered: int
    expected_despatch_date: date | None


class OrdersPage(BaseModel):
    orders: list[OrderSummaryOut]
    next_cursor: str | None


class BackordersPage(BaseModel):
    items: list[BackorderLineOut]
    next_cursor: str | None


class SubmitBasketRequest(BaseModel):
    """POST /basket/submit body."""
    delivery_address_id: UUID | None = None
    delivery_address: AddressIn | None = None       # one-off address (not saved)
    billing_address_id: UUID | None = None

    @model_validator(mode="after")
    def require_delivery(self) -> "SubmitBasketRequest":
        if self.delivery_address_id is None and self.delivery_address is None:
            raise ValueError(
                "Provide either delivery_address_id (saved) or delivery_address (one-off)"
            )
        return self


# ─── Invoices ─────────────────────────────────────────────────────────────────

class InvoiceOut(BaseModel):
    id: UUID
    order_line_id: UUID
    invoice_number: str
    invoice_date: date
    net_gbp: Decimal
    vat_gbp: Decimal
    gross_gbp: Decimal

    model_config = {"from_attributes": True}
