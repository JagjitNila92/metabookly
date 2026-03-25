"""Retailer settings (notification toggles) and address book.

Revision ID: 0010
Revises: 0009
Create Date: 2026-03-22
"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import UUID

revision = "0010"
down_revision = "0009"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # retailer_settings — 1:1 with retailers, auto-created on first access
    op.create_table(
        "retailer_settings",
        sa.Column("retailer_id", UUID(as_uuid=True),
                  sa.ForeignKey("retailers.id", ondelete="CASCADE"),
                  primary_key=True),
        sa.Column("notify_order_submitted", sa.Boolean(), nullable=False, server_default="true"),
        sa.Column("notify_backorder_alert", sa.Boolean(), nullable=False, server_default="true"),
        sa.Column("notify_invoice_available", sa.Boolean(), nullable=False, server_default="true"),
        sa.Column("updated_at", sa.DateTime(), server_default=sa.func.now()),
    )

    # retailer_addresses — billing and delivery address book
    op.create_table(
        "retailer_addresses",
        sa.Column("id", UUID(as_uuid=True), primary_key=True),
        sa.Column("retailer_id", UUID(as_uuid=True),
                  sa.ForeignKey("retailers.id", ondelete="CASCADE"),
                  nullable=False),
        sa.Column("address_type", sa.Text(), nullable=False),   # 'billing' | 'delivery'
        sa.Column("label", sa.Text(), nullable=False),          # e.g. 'Main Shop', 'Warehouse'
        sa.Column("contact_name", sa.Text(), nullable=False),
        sa.Column("line1", sa.Text(), nullable=False),
        sa.Column("line2", sa.Text()),
        sa.Column("city", sa.Text(), nullable=False),
        sa.Column("county", sa.Text()),
        sa.Column("postcode", sa.Text(), nullable=False),
        sa.Column("country_code", sa.Text(), nullable=False, server_default="'GB'"),
        sa.Column("is_default", sa.Boolean(), nullable=False, server_default="false"),
        sa.Column("created_at", sa.DateTime(), server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(), server_default=sa.func.now()),
    )
    op.create_index("retailer_addresses_retailer_id_idx", "retailer_addresses", ["retailer_id"])
    op.create_index("retailer_addresses_type_idx", "retailer_addresses",
                    ["retailer_id", "address_type"])


def downgrade() -> None:
    op.drop_table("retailer_addresses")
    op.drop_table("retailer_settings")
