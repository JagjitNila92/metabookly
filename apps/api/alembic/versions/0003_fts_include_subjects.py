"""Update FTS trigger to include contributor names and subject headings

Revision ID: 0003
Revises: 0002
Create Date: 2026-03-17
"""
from alembic import op

revision = "0003"
down_revision = "0002"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Replace the trigger function to pull in subject headings (weight C)
    # and contributor names (weight B) via subqueries — rebuilds on any book change.
    op.execute("""
        CREATE OR REPLACE FUNCTION books_search_vector_update() RETURNS TRIGGER AS $$
        DECLARE
            v_subjects TEXT;
            v_contributors TEXT;
        BEGIN
            SELECT coalesce(string_agg(subject_heading, ' '), '')
            INTO v_subjects
            FROM book_subjects
            WHERE book_id = NEW.id AND subject_heading IS NOT NULL;

            SELECT coalesce(string_agg(person_name, ' '), '')
            INTO v_contributors
            FROM book_contributors
            WHERE book_id = NEW.id;

            NEW.search_vector :=
                setweight(to_tsvector('english', unaccent(coalesce(NEW.title, ''))), 'A') ||
                setweight(to_tsvector('english', unaccent(coalesce(NEW.subtitle, ''))), 'B') ||
                setweight(to_tsvector('english', unaccent(v_contributors)), 'B') ||
                setweight(to_tsvector('english', unaccent(v_subjects)), 'C') ||
                setweight(to_tsvector('english', unaccent(coalesce(NEW.description, ''))), 'D');
            RETURN NEW;
        END;
        $$ LANGUAGE plpgsql;
    """)

    # Force-rebuild all existing search vectors
    op.execute("UPDATE books SET updated_at = now()")


def downgrade() -> None:
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
    op.execute("UPDATE books SET updated_at = now()")
