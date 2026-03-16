"""Initial schema

Revision ID: 0001
Revises:
Create Date: 2026-03-16
"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision = "0001"
down_revision = None
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Extensions
    op.execute('CREATE EXTENSION IF NOT EXISTS "pgcrypto"')
    op.execute('CREATE EXTENSION IF NOT EXISTS "unaccent"')

    # ── publishers ────────────────────────────────────────────────
    op.create_table(
        "publishers",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True,
                  server_default=sa.text("gen_random_uuid()")),
        sa.Column("name", sa.Text, nullable=False),
        sa.Column("imprint", sa.Text),
        sa.Column("country_code", sa.Text),
        sa.Column("created_at", sa.TIMESTAMP(timezone=True), nullable=False,
                  server_default=sa.text("now()")),
        sa.Column("updated_at", sa.TIMESTAMP(timezone=True), nullable=False,
                  server_default=sa.text("now()")),
        sa.UniqueConstraint("name", name="uq_publishers_name"),
    )

    # ── books ─────────────────────────────────────────────────────
    op.create_table(
        "books",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True,
                  server_default=sa.text("gen_random_uuid()")),
        sa.Column("isbn13", sa.Text, nullable=False),
        sa.Column("isbn10", sa.Text),
        sa.Column("title", sa.Text, nullable=False),
        sa.Column("subtitle", sa.Text),
        sa.Column("publisher_id", postgresql.UUID(as_uuid=True),
                  sa.ForeignKey("publishers.id", ondelete="SET NULL")),
        sa.Column("imprint", sa.Text),
        sa.Column("edition_number", sa.SmallInteger),
        sa.Column("edition_statement", sa.Text),
        sa.Column("language_code", sa.Text, nullable=False, server_default="eng"),
        sa.Column("product_form", sa.Text, nullable=False),
        sa.Column("product_form_detail", sa.Text),
        sa.Column("page_count", sa.SmallInteger),
        sa.Column("description", sa.Text),
        sa.Column("toc", sa.Text),
        sa.Column("excerpt", sa.Text),
        sa.Column("audience_code", sa.Text),
        sa.Column("publication_date", sa.Date),
        sa.Column("out_of_print", sa.Boolean, nullable=False, server_default="false"),
        sa.Column("onix_record_ref", sa.Text),
        sa.Column("cover_image_url", sa.Text),
        sa.Column("search_vector", postgresql.TSVECTOR),
        sa.Column("created_at", sa.TIMESTAMP(timezone=True), nullable=False,
                  server_default=sa.text("now()")),
        sa.Column("updated_at", sa.TIMESTAMP(timezone=True), nullable=False,
                  server_default=sa.text("now()")),
        sa.UniqueConstraint("isbn13", name="uq_books_isbn13"),
    )
    op.create_index("books_search_vector_idx", "books", ["search_vector"],
                    postgresql_using="gin")
    op.create_index("books_publisher_id_idx", "books", ["publisher_id"])
    op.create_index("books_product_form_idx", "books", ["product_form"])
    op.create_index("books_publication_date_idx", "books", ["publication_date"])
    op.create_index("books_out_of_print_idx", "books", ["out_of_print"])

    # FTS trigger — updates search_vector on INSERT or UPDATE
    op.execute("""
        CREATE OR REPLACE FUNCTION books_search_vector_update() RETURNS TRIGGER AS $$
        BEGIN
            NEW.search_vector :=
                setweight(to_tsvector('english', unaccent(coalesce(NEW.title, ''))), 'A') ||
                setweight(to_tsvector('english', unaccent(coalesce(NEW.subtitle, ''))), 'B') ||
                setweight(to_tsvector('english', unaccent(coalesce(NEW.description, ''))), 'D');
            RETURN NEW;
        END;
        $$ LANGUAGE plpgsql;
    """)
    op.execute("""
        CREATE TRIGGER books_search_vector_trigger
            BEFORE INSERT OR UPDATE ON books
            FOR EACH ROW EXECUTE FUNCTION books_search_vector_update();
    """)

    # ── book_contributors ─────────────────────────────────────────
    op.create_table(
        "book_contributors",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True,
                  server_default=sa.text("gen_random_uuid()")),
        sa.Column("book_id", postgresql.UUID(as_uuid=True),
                  sa.ForeignKey("books.id", ondelete="CASCADE"), nullable=False),
        sa.Column("sequence_number", sa.SmallInteger, nullable=False, server_default="1"),
        sa.Column("role_code", sa.Text, nullable=False),
        sa.Column("person_name", sa.Text, nullable=False),
        sa.Column("person_name_inverted", sa.Text),
        sa.Column("bio", sa.Text),
        sa.Column("created_at", sa.TIMESTAMP(timezone=True), nullable=False,
                  server_default=sa.text("now()")),
    )
    op.create_index("book_contributors_book_id_idx", "book_contributors", ["book_id"])
    op.create_index(
        "book_contributors_author_name_idx",
        "book_contributors", ["person_name"],
        postgresql_where=sa.text("role_code = 'A01'"),
    )

    # ── book_subjects ─────────────────────────────────────────────
    op.create_table(
        "book_subjects",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True,
                  server_default=sa.text("gen_random_uuid()")),
        sa.Column("book_id", postgresql.UUID(as_uuid=True),
                  sa.ForeignKey("books.id", ondelete="CASCADE"), nullable=False),
        sa.Column("scheme_id", sa.Text, nullable=False),
        sa.Column("subject_code", sa.Text, nullable=False),
        sa.Column("subject_heading", sa.Text),
        sa.Column("main_subject", sa.Boolean, nullable=False, server_default="false"),
        sa.Column("created_at", sa.TIMESTAMP(timezone=True), nullable=False,
                  server_default=sa.text("now()")),
    )
    op.create_index("book_subjects_book_id_idx", "book_subjects", ["book_id"])
    op.create_index("book_subjects_scheme_code_idx", "book_subjects",
                    ["scheme_id", "subject_code"])

    # ── retailers ─────────────────────────────────────────────────
    op.create_table(
        "retailers",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True,
                  server_default=sa.text("gen_random_uuid()")),
        sa.Column("cognito_sub", sa.Text, nullable=False),
        sa.Column("company_name", sa.Text, nullable=False),
        sa.Column("san", sa.Text),
        sa.Column("email", sa.Text, nullable=False),
        sa.Column("country_code", sa.Text, nullable=False, server_default="GB"),
        sa.Column("active", sa.Boolean, nullable=False, server_default="true"),
        sa.Column("created_at", sa.TIMESTAMP(timezone=True), nullable=False,
                  server_default=sa.text("now()")),
        sa.Column("updated_at", sa.TIMESTAMP(timezone=True), nullable=False,
                  server_default=sa.text("now()")),
        sa.UniqueConstraint("cognito_sub", name="uq_retailers_cognito_sub"),
        sa.UniqueConstraint("email", name="uq_retailers_email"),
    )

    # ── retailer_distributors ─────────────────────────────────────
    op.create_table(
        "retailer_distributors",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True,
                  server_default=sa.text("gen_random_uuid()")),
        sa.Column("retailer_id", postgresql.UUID(as_uuid=True),
                  sa.ForeignKey("retailers.id", ondelete="CASCADE"), nullable=False),
        sa.Column("distributor_code", sa.Text, nullable=False),
        sa.Column("account_number", sa.Text),
        sa.Column("active", sa.Boolean, nullable=False, server_default="true"),
        sa.Column("created_at", sa.TIMESTAMP(timezone=True), nullable=False,
                  server_default=sa.text("now()")),
        sa.UniqueConstraint("retailer_id", "distributor_code",
                            name="uq_retailer_distributors_retailer_id"),
    )
    op.create_index("retailer_distributors_retailer_id_idx",
                    "retailer_distributors", ["retailer_id"])

    # ── onix_feeds ────────────────────────────────────────────────
    op.create_table(
        "onix_feeds",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True,
                  server_default=sa.text("gen_random_uuid()")),
        sa.Column("s3_bucket", sa.Text, nullable=False),
        sa.Column("s3_key", sa.Text, nullable=False),
        sa.Column("file_size_bytes", sa.BigInteger),
        sa.Column("status", sa.Text, nullable=False, server_default="pending"),
        sa.Column("records_found", sa.Integer),
        sa.Column("records_upserted", sa.Integer),
        sa.Column("records_failed", sa.Integer),
        sa.Column("error_detail", sa.Text),
        sa.Column("triggered_by", sa.Text),
        sa.Column("started_at", sa.TIMESTAMP(timezone=True)),
        sa.Column("completed_at", sa.TIMESTAMP(timezone=True)),
        sa.Column("created_at", sa.TIMESTAMP(timezone=True), nullable=False,
                  server_default=sa.text("now()")),
    )
    op.create_index("onix_feeds_status_idx", "onix_feeds", ["status"])
    op.create_index("onix_feeds_created_at_idx", "onix_feeds", ["created_at"])


def downgrade() -> None:
    op.execute("DROP TRIGGER IF EXISTS books_search_vector_trigger ON books")
    op.execute("DROP FUNCTION IF EXISTS books_search_vector_update()")
    op.drop_table("onix_feeds")
    op.drop_table("retailer_distributors")
    op.drop_table("retailers")
    op.drop_table("book_subjects")
    op.drop_table("book_contributors")
    op.drop_table("books")
    op.drop_table("publishers")
