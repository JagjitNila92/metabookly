"""
Metadata quality scoring service.

Scores each book 0–100 based on field completeness:

  Required (40 pts) — blocking fields without which a title is basically invisible:
    ISBN-13           always present (it's the PK lookup) — no points, assumed
    title             always present — assumed
    publisher         +10
    publication_date  +10
    product_form      always present — assumed
    uk_rights stated  +10
    rrp_gbp           +10

  High value (35 pts) — fields that drive discoverability and bookseller decisions:
    description ≥150 chars   +20
    cover_image_url          +10
    ≥1 subject heading       +5

  Nice to have (25 pts) — enrich the record and help AI/recommendations:
    contributor with bio     +8
    toc or excerpt           +7
    page_count               +5
    height_mm + width_mm     +5

Total possible: 100.

The score is computed in-process and written directly to Book.metadata_score.
"""
from __future__ import annotations

import uuid
from typing import Sequence

from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.book import Book, BookContributor, BookSubject


def compute_score(
    book: Book,
    has_subjects: bool,
    has_contributor_with_bio: bool,
) -> int:
    score = 0

    # ── Required block (40 pts) ───────────────────────────────────────────────
    if book.publisher_id is not None:
        score += 10
    if book.publication_date is not None:
        score += 10
    if book.uk_rights is not None:   # True or False — either way it's stated
        score += 10
    if book.rrp_gbp is not None:
        score += 10

    # ── High value (35 pts) ───────────────────────────────────────────────────
    if book.description and len(book.description) >= 150:
        score += 20
    elif book.description and len(book.description) >= 50:
        score += 8   # partial credit for short description
    if book.cover_image_url:
        score += 10
    if has_subjects:
        score += 5

    # ── Nice to have (25 pts) ─────────────────────────────────────────────────
    if has_contributor_with_bio:
        score += 8
    if book.toc or book.excerpt:
        score += 7
    if book.page_count:
        score += 5
    if book.height_mm and book.width_mm:
        score += 5

    return min(score, 100)


async def score_books(session: AsyncSession, book_ids: Sequence[uuid.UUID]) -> int:
    """
    Compute and persist metadata_score for a list of book IDs.
    Called after every portal ingest with the list of upserted book IDs.
    Returns the number of books scored.
    """
    if not book_ids:
        return 0

    # Fetch all books
    books = (
        await session.execute(
            select(Book).where(Book.id.in_(book_ids))
        )
    ).scalars().all()

    if not books:
        return 0

    # Fetch which books have ≥1 subject
    subject_book_ids = set(
        (await session.execute(
            select(BookSubject.book_id)
            .where(BookSubject.book_id.in_(book_ids))
            .distinct()
        )).scalars().all()
    )

    # Fetch which books have ≥1 contributor with a bio
    contributor_bio_ids = set(
        (await session.execute(
            select(BookContributor.book_id)
            .where(
                BookContributor.book_id.in_(book_ids),
                BookContributor.bio.isnot(None),
                func.length(BookContributor.bio) > 20,
            )
            .distinct()
        )).scalars().all()
    )

    for book in books:
        book.metadata_score = compute_score(
            book,
            has_subjects=book.id in subject_book_ids,
            has_contributor_with_bio=book.id in contributor_bio_ids,
        )

    return len(books)


async def get_quality_summary(
    session: AsyncSession,
    feed_source_id: uuid.UUID,
) -> dict:
    """
    Return a quality summary for all books ingested from a given feed source.
    Used by GET /portal/quality.
    """
    from app.models.portal import BookDistributor

    # Books belonging to this publisher
    book_ids_subq = (
        select(BookDistributor.book_id)
        .where(BookDistributor.feed_source_id == feed_source_id)
        .scalar_subquery()
    )

    result = await session.execute(
        select(
            func.count(Book.id).label("total"),
            func.avg(Book.metadata_score).label("avg_score"),
            func.count(Book.id).filter(Book.metadata_score < 60).label("below_60"),
            func.count(Book.id).filter(Book.cover_image_url.is_(None)).label("missing_cover"),
            func.count(Book.id).filter(
                (Book.description.is_(None)) | (func.length(Book.description) < 150)
            ).label("short_or_no_description"),
            func.count(Book.id).filter(Book.rrp_gbp.is_(None)).label("missing_price"),
            func.count(Book.id).filter(Book.publication_date.is_(None)).label("missing_pub_date"),
        )
        .where(Book.id.in_(book_ids_subq), Book.out_of_print == False)  # noqa: E712
    )
    row = result.one()

    # Titles with worst scores — fetch full fields so we can show what's missing
    worst_rows = (await session.execute(
        select(
            Book.isbn13, Book.title, Book.metadata_score,
            Book.description, Book.cover_image_url, Book.rrp_gbp,
            Book.publication_date, Book.publisher_id, Book.uk_rights,
            Book.toc, Book.excerpt, Book.page_count,
        )
        .where(Book.id.in_(book_ids_subq), Book.out_of_print == False)  # noqa: E712
        .order_by(Book.metadata_score.asc().nulls_first())
        .limit(10)
    )).all()

    def _missing_fields(r) -> list[str]:
        """Return plain-English labels for fields that would improve the score."""
        missing = []
        if not r.publisher_id:
            missing.append("Publisher name")
        if not r.publication_date:
            missing.append("Publication date")
        if r.uk_rights is None:
            missing.append("UK rights")
        if not r.rrp_gbp:
            missing.append("GBP price")
        if not r.description or len(r.description) < 150:
            missing.append("Full description" if not r.description else "Longer description")
        if not r.cover_image_url:
            missing.append("Cover image")
        if not r.toc and not r.excerpt:
            missing.append("TOC or excerpt")
        if not r.page_count:
            missing.append("Page count")
        return missing

    # Top issues ranked by frequency
    issues = []
    if row.short_or_no_description:
        issues.append({
            "issue": "Missing or short description",
            "count": row.short_or_no_description,
            "points": 20,
            "tip": "Booksellers use descriptions to decide what to stock and recommend. Aim for at least 150 characters.",
            "how_to_fix": "Add a description of at least 150 characters to your ONIX feed in the <TextContent> block (TextType 03).",
        })
    if row.missing_cover:
        issues.append({
            "issue": "No cover image",
            "count": row.missing_cover,
            "points": 10,
            "tip": "Titles without covers are 3× less likely to be ordered by booksellers.",
            "how_to_fix": "Add a cover URL to your ONIX feed via <SupportingResource>, or upload one directly on the book detail page.",
        })
    if row.missing_price:
        issues.append({
            "issue": "Missing GBP price",
            "count": row.missing_price,
            "points": 10,
            "tip": "Without a price, booksellers can't assess margin or place orders.",
            "how_to_fix": "Include a GBP list price in <ProductSupply> → <SupplyDetail> → <Price> with CurrencyCode GBP.",
        })
    if row.missing_pub_date:
        issues.append({
            "issue": "Missing publication date",
            "count": row.missing_pub_date,
            "points": 10,
            "tip": "Publication date helps booksellers plan events and new release promotions.",
            "how_to_fix": "Add <PublishingDate> with DateRole 01 (publication date) in YYYYMMDD format.",
        })
    issues.sort(key=lambda x: x["count"], reverse=True)

    return {
        "total_titles": row.total or 0,
        "avg_score": round(float(row.avg_score or 0), 1),
        "titles_below_60": row.below_60 or 0,
        "top_issues": issues[:4],
        "worst_titles": [
            {
                "isbn13": r.isbn13,
                "title": r.title,
                "score": r.metadata_score,
                "missing": _missing_fields(r),
            }
            for r in worst_rows
        ],
    }
