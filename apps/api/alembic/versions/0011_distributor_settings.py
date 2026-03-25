"""Distributor settings — drop-ship flag and minimum order value per distributor.

Revision ID: 0011
Revises: 0010
Create Date: 2026-03-22
"""
from alembic import op
import sqlalchemy as sa

revision = "0011"
down_revision = "0010"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # distributor_settings — keyed by distributor_code, managed by Metabookly admins
    op.create_table(
        "distributor_settings",
        sa.Column("distributor_code", sa.Text(), primary_key=True),
        sa.Column("allows_dropship", sa.Boolean(), nullable=False, server_default="false"),
        sa.Column("min_order_value_gbp", sa.Numeric(8, 2)),    # NULL = no minimum
        sa.Column("updated_at", sa.DateTime(), server_default=sa.func.now()),
    )

    # Seed mock distributor settings for dev/demo
    op.execute(
        """
        INSERT INTO distributor_settings (distributor_code, allows_dropship, min_order_value_gbp)
        VALUES ('MOCK', false, NULL)
        ON CONFLICT DO NOTHING
        """
    )


def downgrade() -> None:
    op.drop_table("distributor_settings")
