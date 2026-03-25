"""Drop unique constraint on retailers.email — cognito_sub is the real unique key.

Email uniqueness is already enforced by Cognito. Access tokens don't carry email
claims, so the email column can legitimately be empty on auto-creation and filled
in later via a profile update.

Revision ID: 0008
Revises: 0007
Create Date: 2026-03-18
"""
from alembic import op

revision = "0008"
down_revision = "0007"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Drop the unique constraint — Cognito enforces email uniqueness upstream
    op.drop_constraint("uq_retailers_email", "retailers", type_="unique")

    # Remove orphaned rows where email is empty and no real user data exists
    # (these were created by failed first-login attempts before this fix)
    op.execute(
        """
        DELETE FROM retailers
        WHERE email = ''
          AND company_name IN ('', 'My New Bookshop')
          AND NOT EXISTS (
              SELECT 1 FROM retailer_distributors
              WHERE retailer_distributors.retailer_id = retailers.id
          )
        """
    )


def downgrade() -> None:
    op.create_unique_constraint("uq_retailers_email", "retailers", ["email"])
