"""Orders, order lines, order line items, and invoices.

Revision ID: 0012
Revises: 0011
Create Date: 2026-03-22
"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import JSONB, UUID

revision = "0012"
down_revision = "0011"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # orders — one per submit, can span multiple distributors via order_lines
    op.create_table(
        "orders",
        sa.Column("id", UUID(as_uuid=True), primary_key=True),
        sa.Column("retailer_id", UUID(as_uuid=True),
                  sa.ForeignKey("retailers.id", ondelete="RESTRICT"),
                  nullable=False),
        sa.Column("po_number", sa.Text(), nullable=False, unique=True),  # idempotency key
        sa.Column("status", sa.Text(), nullable=False, server_default="'draft'"),
        # Addresses — saved reference (may be NULL if one-off used)
        sa.Column("billing_address_id", UUID(as_uuid=True),
                  sa.ForeignKey("retailer_addresses.id", ondelete="SET NULL")),
        sa.Column("delivery_address_id", UUID(as_uuid=True),
                  sa.ForeignKey("retailer_addresses.id", ondelete="SET NULL")),
        # Snapshot of delivery address at order time (frozen even if address later changes/deleted)
        sa.Column("delivery_address_snapshot", JSONB),
        sa.Column("delivery_type", sa.Text(), nullable=False, server_default="'stock'"),
        sa.Column("total_lines", sa.Integer()),
        sa.Column("total_gbp", sa.Numeric(10, 2)),
        sa.Column("submitted_at", sa.DateTime()),
        sa.Column("created_at", sa.DateTime(), server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(), server_default=sa.func.now()),
    )
    op.create_index("orders_retailer_id_idx", "orders", ["retailer_id"])
    op.create_index("orders_status_idx", "orders", ["status"])
    op.create_index("orders_submitted_at_idx", "orders", ["submitted_at"])
    op.create_index("orders_retailer_status_idx", "orders", ["retailer_id", "status"])

    # order_lines — one per distributor per order
    op.create_table(
        "order_lines",
        sa.Column("id", UUID(as_uuid=True), primary_key=True),
        sa.Column("order_id", UUID(as_uuid=True),
                  sa.ForeignKey("orders.id", ondelete="CASCADE"),
                  nullable=False),
        sa.Column("distributor_code", sa.Text(), nullable=False),
        sa.Column("delivery_type", sa.Text(), nullable=False, server_default="'stock'"),
        sa.Column("status", sa.Text(), nullable=False, server_default="'pending'"),
        sa.Column("transmission_attempts", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("last_attempted_at", sa.DateTime()),
        sa.Column("external_po_ref", sa.Text()),        # distributor's reference for our PO
        sa.Column("despatch_note_ref", sa.Text()),
        sa.Column("tracking_ref", sa.Text()),
        sa.Column("estimated_delivery_date", sa.Date()),
        sa.Column("subtotal_gbp", sa.Numeric(10, 2)),
        sa.Column("created_at", sa.DateTime(), server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(), server_default=sa.func.now()),
    )
    op.create_index("order_lines_order_id_idx", "order_lines", ["order_id"])
    op.create_index("order_lines_distributor_idx", "order_lines", ["distributor_code"])
    op.create_index("order_lines_status_idx", "order_lines", ["status"])

    # order_line_items — one per book per order_line
    op.create_table(
        "order_line_items",
        sa.Column("id", UUID(as_uuid=True), primary_key=True),
        sa.Column("order_line_id", UUID(as_uuid=True),
                  sa.ForeignKey("order_lines.id", ondelete="CASCADE"),
                  nullable=False),
        sa.Column("book_id", UUID(as_uuid=True),
                  sa.ForeignKey("books.id", ondelete="RESTRICT"),
                  nullable=False),
        sa.Column("isbn13", sa.Text(), nullable=False),
        sa.Column("retailer_line_ref", sa.Text(), nullable=False),   # {order_line_id}-{seq}, echoed in ORDRSP
        sa.Column("quantity_ordered", sa.Integer(), nullable=False),
        sa.Column("quantity_confirmed", sa.Integer()),
        sa.Column("quantity_despatched", sa.Integer()),
        sa.Column("quantity_invoiced", sa.Integer()),
        sa.Column("status", sa.Text(), nullable=False, server_default="'pending'"),
        sa.Column("expected_despatch_date", sa.Date()),
        sa.Column("trade_price_gbp", sa.Numeric(10, 2)),
        sa.Column("rrp_gbp", sa.Numeric(10, 2)),           # snapshot at order time
        sa.Column("created_at", sa.DateTime(), server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(), server_default=sa.func.now()),
    )
    op.create_index("order_line_items_line_id_idx", "order_line_items", ["order_line_id"])
    op.create_index("order_line_items_status_idx", "order_line_items", ["status"])
    op.create_index("order_line_items_isbn13_idx", "order_line_items", ["isbn13"])

    # invoices — one per order_line when INVOIC received
    op.create_table(
        "invoices",
        sa.Column("id", UUID(as_uuid=True), primary_key=True),
        sa.Column("order_line_id", UUID(as_uuid=True),
                  sa.ForeignKey("order_lines.id", ondelete="CASCADE"),
                  nullable=False, unique=True),
        sa.Column("invoice_number", sa.Text(), nullable=False),
        sa.Column("invoice_date", sa.Date(), nullable=False),
        sa.Column("net_gbp", sa.Numeric(10, 2), nullable=False),
        sa.Column("vat_gbp", sa.Numeric(10, 2), nullable=False, server_default="0"),
        sa.Column("gross_gbp", sa.Numeric(10, 2), nullable=False),
        sa.Column("raw_edi", sa.Text()),                   # original EDI document for audit
        sa.Column("created_at", sa.DateTime(), server_default=sa.func.now()),
    )
    op.create_index("invoices_order_line_id_idx", "invoices", ["order_line_id"])


def downgrade() -> None:
    op.drop_table("invoices")
    op.drop_table("order_line_items")
    op.drop_table("order_lines")
    op.drop_table("orders")
