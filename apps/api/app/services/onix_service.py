"""ONIX ingest service.

Orchestrates the full pipeline:
  1. Parse ONIX 3.0 XML (streaming, memory-bounded)
  2. For each parsed product:
     a. Upsert Publisher (by name)
     b. Upsert Book (by isbn13) — all scalar fields
     c. Replace BookContributors (delete existing + insert fresh)
     d. Replace BookSubjects (delete existing + insert fresh)
     e. Handle NotificationType 05 (delete) — marks book out_of_print
  3. Update the OnixFeed record with final counts and status

All DB operations use async SQLAlchemy 2.0 with PostgreSQL upserts.
"""
from __future__ import annotations

import uuid
from datetime import datetime, timezone, UTC
from io import BytesIO
from pathlib import Path
from typing import IO

from sqlalchemy import delete, select, text
from sqlalchemy.dialects.postgresql import insert as pg_insert
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.book import Book, BookContributor, BookSubject, Publisher
from app.models.onix_feed import OnixFeed
from app.parsers.onix3 import ParsedBook, parse_onix_file


async def _upsert_publisher(session: AsyncSession, name: str) -> uuid.UUID:
    """Insert publisher if not exists, return its UUID."""
    stmt = (
        pg_insert(Publisher)
        .values(name=name)
        .on_conflict_do_update(
            index_elements=["name"],
            set_={"updated_at": text("now()")},
        )
        .returning(Publisher.id)
    )
    result = await session.execute(stmt)
    return result.scalar_one()


async def _ingest_book(session: AsyncSession, book: ParsedBook) -> None:
    """Upsert one parsed book and its contributors/subjects."""

    # ── Handle delete notifications ──────────────────────────────────────────
    if book.notification_type == "05":
        await session.execute(
            text("UPDATE books SET out_of_print = true, updated_at = now() WHERE isbn13 = :isbn")
            .bindparams(isbn=book.isbn13)
        )
        return

    # ── Resolve publisher ────────────────────────────────────────────────────
    publisher_id: uuid.UUID | None = None
    if book.publisher_name:
        publisher_id = await _upsert_publisher(session, book.publisher_name)

    # ── Upsert book ──────────────────────────────────────────────────────────
    book_values = {
        "isbn13": book.isbn13,
        "isbn10": book.isbn10,
        "title": book.title,
        "subtitle": book.subtitle,
        "publisher_id": publisher_id,
        "imprint": book.imprint_name,
        "edition_number": book.edition_number,
        "edition_statement": book.edition_statement,
        "language_code": book.language_code,
        "product_form": book.product_form,
        "product_form_detail": book.product_form_detail,
        "page_count": book.page_count,
        "description": book.description,
        "toc": book.toc,
        "excerpt": book.excerpt,
        "audience_code": book.audience_code,
        "publication_date": book.publication_date,
        "publishing_status": book.publishing_status,
        "out_of_print": book.out_of_print,
        "onix_record_ref": book.record_ref,
        "cover_image_url": book.cover_image_url,
        "uk_rights": book.uk_rights,
        "rrp_gbp": book.rrp_gbp,
        "rrp_usd": book.rrp_usd,
        "height_mm": book.height_mm,
        "width_mm": book.width_mm,
    }

    stmt = (
        pg_insert(Book)
        .values(**book_values)
        .on_conflict_do_update(
            index_elements=["isbn13"],
            set_={k: v for k, v in book_values.items() if k != "isbn13"},
        )
        .returning(Book.id)
    )
    result = await session.execute(stmt)
    book_id: uuid.UUID = result.scalar_one()

    # ── Replace contributors ─────────────────────────────────────────────────
    await session.execute(delete(BookContributor).where(BookContributor.book_id == book_id))
    if book.contributors:
        await session.execute(
            pg_insert(BookContributor),
            [
                {
                    "book_id": book_id,
                    "sequence_number": c.sequence_number,
                    "role_code": c.role_code,
                    "person_name": c.person_name,
                    "person_name_inverted": c.person_name_inverted,
                    "bio": c.bio,
                }
                for c in book.contributors
            ],
        )

    # ── Replace subjects ─────────────────────────────────────────────────────
    await session.execute(delete(BookSubject).where(BookSubject.book_id == book_id))
    if book.subjects:
        await session.execute(
            pg_insert(BookSubject),
            [
                {
                    "book_id": book_id,
                    "scheme_id": s.scheme_id,
                    "subject_code": s.subject_code,
                    "subject_heading": s.subject_heading,
                    "main_subject": s.main_subject,
                }
                for s in book.subjects
            ],
        )


async def ingest_onix(
    session: AsyncSession,
    source: str | Path | bytes | IO[bytes],
    *,
    feed_id: uuid.UUID | None = None,
    triggered_by: str = "api",
    s3_bucket: str = "direct-upload",
    s3_key: str = "direct-upload",
) -> dict:
    """
    Parse and ingest an ONIX 3.0 file.

    Returns a summary dict with: feed_id, status, records_found,
    records_upserted, records_failed, errors.
    """
    # ── Create / update feed record ──────────────────────────────────────────
    if feed_id is None:
        feed_id = uuid.uuid4()

    feed = OnixFeed(
        id=feed_id,
        s3_bucket=s3_bucket,
        s3_key=s3_key,
        status="processing",
        triggered_by=triggered_by,
        started_at=datetime.now(UTC).replace(tzinfo=None),
    )
    session.add(feed)
    await session.flush()

    found = 0
    upserted = 0
    failed = 0
    errors: list[str] = []

    try:
        for parsed_book in parse_onix_file(source):
            found += 1
            try:
                await _ingest_book(session, parsed_book)
                upserted += 1
            except Exception as exc:
                failed += 1
                if len(errors) < 20:
                    errors.append(f"ISBN {parsed_book.isbn13}: {exc}")
                # Continue processing remaining books — don't abort the whole feed

        status = "completed" if failed == 0 else "completed_with_errors"

    except Exception as exc:
        status = "failed"
        errors.append(f"Feed-level error: {exc}")

    # ── Finalise feed record ─────────────────────────────────────────────────
    feed.status = status
    feed.records_found = found
    feed.records_upserted = upserted
    feed.records_failed = failed
    feed.error_detail = "; ".join(errors) if errors else None
    feed.completed_at = datetime.now(UTC).replace(tzinfo=None)
    await session.flush()

    return {
        "feed_id": str(feed_id),
        "status": status,
        "records_found": found,
        "records_upserted": upserted,
        "records_failed": failed,
        "errors": errors,
    }
