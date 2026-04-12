"""
Bedrock AI enrichment service.

Called after portal ingest completes (descriptions) or on-demand (TOC, excerpt).
High-confidence suggestions are auto-accepted immediately; medium/low are queued
for publisher review.

Supported fields:
  description — generated after every ingest for books with thin/missing descriptions
  toc         — on-demand; structured chapter list for non-fiction / academic titles
  excerpt     — on-demand; suggested opening passage
"""
from __future__ import annotations

import asyncio
import json
import logging
import uuid
from typing import Literal

import boto3
from sqlalchemy import cast, select
from sqlalchemy.dialects.postgresql import JSONB, insert as pg_insert
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import get_settings
from app.models.book import Book, BookContributor, BookSubject, Publisher
from app.models.portal import AiSuggestion, BookEditorialLayer

logger = logging.getLogger(__name__)

# Skip AI enrichment if description already meets this length
_THIN_THRESHOLD = 100

SupportedField = Literal["description", "toc", "excerpt"]


# ─── Bedrock call (synchronous — run in executor) ─────────────────────────────

def _call_bedrock(model_id: str, region: str, prompt: str) -> dict:
    """Invoke a Bedrock Claude model and return parsed JSON response."""
    client = boto3.client("bedrock-runtime", region_name=region)
    body = json.dumps({
        "anthropic_version": "bedrock-2023-05-31",
        "max_tokens": 600,
        "messages": [{"role": "user", "content": prompt}],
    })
    response = client.invoke_model(
        modelId=model_id,
        body=body,
        contentType="application/json",
        accept="application/json",
    )
    result = json.loads(response["body"].read())
    return json.loads(result["content"][0]["text"])


def _build_description_prompt(
    title: str,
    publisher_name: str | None,
    product_form: str | None,
    existing_description: str | None,
    contributor_names: list[str],
    subject_headings: list[str],
) -> str:
    contrib_str = ", ".join(contributor_names) if contributor_names else "Unknown"
    subject_str = ", ".join(subject_headings) if subject_headings else "Unclassified"

    return f"""You are a book metadata specialist writing for a UK trade catalogue.

Generate a compelling description for the following book and rate your confidence.

Book details:
- Title: {title}
- Author(s): {contrib_str}
- Publisher: {publisher_name or "Unknown"}
- Format: {product_form or "Unknown"}
- Subjects: {subject_str}
- Existing description: {existing_description or "None"}

Instructions:
- Write 2-3 paragraphs, 150-250 words total
- Professional tone suited to bookseller and librarian audiences
- Do not begin with "This book" or repeat the title in the first sentence
- Confidence rating: "high" if you have subjects AND contributor names, \
"medium" if you have one of them, "low" if very limited metadata

Return ONLY valid JSON with exactly this structure (no markdown, no preamble):
{{"description": "...", "confidence": "high|medium|low", "reasoning": "one brief sentence"}}"""


# ─── Editorial layer upsert ───────────────────────────────────────────────────

async def _apply_to_editorial_layer(
    session: AsyncSession,
    book_id: uuid.UUID,
    field: str,
    value: str,
) -> None:
    """Write an auto-accepted AI value into the editorial layer."""
    stmt = (
        pg_insert(BookEditorialLayer)
        .values(
            book_id=book_id,
            **{field: value},
            field_sources={field: "ai_accepted"},
        )
        .on_conflict_do_update(
            index_elements=["book_id"],
            set_={
                field: value,
                # Merge into existing field_sources JSON rather than overwriting
                "field_sources": BookEditorialLayer.field_sources.op("||")(
                    cast(json.dumps({field: "ai_accepted"}), JSONB)
                ),
            },
        )
    )
    await session.execute(stmt)


# ─── Main enrichment function ─────────────────────────────────────────────────

async def enrich_books_after_ingest(
    session: AsyncSession,
    book_ids: list[uuid.UUID],
) -> int:
    """
    Generate AI description suggestions for newly ingested books with thin/missing
    descriptions. Returns the number of suggestions created.

    - High confidence  → auto-accepted, applied to editorial layer immediately
    - Medium/low       → queued as pending for publisher review
    - Already-adequate descriptions (>= 100 chars) are skipped
    - Books with a pending suggestion already are skipped (no stacking)
    - Any Bedrock error for a single book is logged and skipped (never fails the ingest)
    """
    if not book_ids:
        return 0

    settings = get_settings()
    model_id = settings.bedrock_model_id
    region = settings.aws_region
    created = 0

    for book_id in book_ids:
        try:
            # Load book
            book = (await session.execute(
                select(Book).where(Book.id == book_id)
            )).scalar_one_or_none()
            if book is None:
                continue

            # Skip if description is already adequate
            existing_description = book.description or ""
            if len(existing_description) >= _THIN_THRESHOLD:
                continue

            # Skip if a pending suggestion already exists for this field
            existing_suggestion = (await session.execute(
                select(AiSuggestion).where(
                    AiSuggestion.book_id == book_id,
                    AiSuggestion.field_name == "description",
                    AiSuggestion.status == "pending",
                )
            )).scalar_one_or_none()
            if existing_suggestion is not None:
                continue

            # Load publisher name (avoid lazy-loading in async context)
            publisher_name: str | None = None
            if book.publisher_id:
                pub = (await session.execute(
                    select(Publisher).where(Publisher.id == book.publisher_id)
                )).scalar_one_or_none()
                publisher_name = pub.name if pub else None

            # Load contributors and subjects
            contributors = list((await session.execute(
                select(BookContributor).where(BookContributor.book_id == book_id)
            )).scalars().all())

            subjects = list((await session.execute(
                select(BookSubject).where(BookSubject.book_id == book_id)
            )).scalars().all())

            contributor_names = [c.person_name for c in contributors if c.person_name]
            subject_headings = [s.subject_heading for s in subjects if s.subject_heading]

            # Build prompt and call Bedrock (synchronous boto3 → thread executor)
            prompt = _build_description_prompt(
                title=book.title,
                publisher_name=publisher_name,
                product_form=book.product_form,
                existing_description=existing_description or None,
                contributor_names=contributor_names,
                subject_headings=subject_headings,
            )
            ai_result = await asyncio.to_thread(_call_bedrock, model_id, region, prompt)

            suggested = ai_result.get("description", "").strip()
            confidence = ai_result.get("confidence", "low")
            reasoning = ai_result.get("reasoning", "")

            if not suggested or confidence not in ("high", "medium", "low"):
                logger.warning("Unexpected AI response for book %s: %s", book_id, ai_result)
                continue

            if confidence == "high":
                status = "auto_accepted"
                await _apply_to_editorial_layer(session, book_id, "description", suggested)
            else:
                status = "pending"

            session.add(AiSuggestion(
                book_id=book_id,
                field_name="description",
                original_value=existing_description or None,
                suggested_value=suggested,
                confidence=confidence,
                model_id=model_id,
                reasoning=reasoning,
                status=status,
            ))
            created += 1
            logger.info(
                "AI suggestion created for book %s (%s): confidence=%s status=%s",
                book_id, book.title, confidence, status,
            )

        except Exception as exc:
            logger.warning("AI enrichment failed for book %s: %s", book_id, exc)

    return created


# ─── TOC prompt ───────────────────────────────────────────────────────────────

def _build_toc_prompt(
    title: str,
    description: str | None,
    contributor_names: list[str],
    subject_headings: list[str],
) -> str:
    contrib_str = ", ".join(contributor_names) if contributor_names else "Unknown"
    subject_str = ", ".join(subject_headings) if subject_headings else "Unclassified"
    desc_str = description[:400] if description else "Not available"

    return f"""You are a book metadata specialist. Generate a plausible table of contents
for the following book, suitable for inclusion in a UK trade catalogue record.

Book details:
- Title: {title}
- Author(s): {contrib_str}
- Subjects: {subject_str}
- Description: {desc_str}

Instructions:
- List 6–12 chapter/section titles only (no page numbers)
- Use a numbered list format: "1. Chapter Title\\n2. Chapter Title\\n..."
- Confidence: "high" if you have description + subjects, "medium" if one of them, "low" otherwise
- Only suggest a TOC if the book is clearly non-fiction, academic, or technical

Return ONLY valid JSON with exactly this structure (no markdown, no preamble):
{{"toc": "1. ...\\n2. ...\\n...", "confidence": "high|medium|low", "reasoning": "one brief sentence"}}"""


# ─── Excerpt prompt ───────────────────────────────────────────────────────────

def _build_excerpt_prompt(
    title: str,
    description: str | None,
    contributor_names: list[str],
    subject_headings: list[str],
) -> str:
    contrib_str = ", ".join(contributor_names) if contributor_names else "Unknown"
    subject_str = ", ".join(subject_headings) if subject_headings else "Unclassified"
    desc_str = description[:400] if description else "Not available"

    return f"""You are a book metadata specialist. Write a short suggested excerpt
(an evocative opening passage) for the following book, suitable for a UK trade catalogue.

Book details:
- Title: {title}
- Author(s): {contrib_str}
- Subjects: {subject_str}
- Description: {desc_str}

Instructions:
- Write 2–3 sentences (60–100 words) in a style matching the genre
- This is a marketing excerpt, not an academic abstract
- Confidence: "high" if you have description + subjects, "medium" if one, "low" otherwise

Return ONLY valid JSON with exactly this structure (no markdown, no preamble):
{{"excerpt": "...", "confidence": "high|medium|low", "reasoning": "one brief sentence"}}"""


# ─── On-demand field generation ───────────────────────────────────────────────

_FIELD_CONFIG: dict[str, dict] = {
    "description": {
        "check_attr": "description",
        "thin_len": _THIN_THRESHOLD,
        "result_key": "description",
    },
    "toc": {
        "check_attr": "toc",
        "thin_len": 20,
        "result_key": "toc",
    },
    "excerpt": {
        "check_attr": "excerpt",
        "thin_len": 20,
        "result_key": "excerpt",
    },
}


async def generate_field_suggestions(
    session: AsyncSession,
    feed_source_id: uuid.UUID,
    field: SupportedField,
    limit: int = 30,
) -> int:
    """
    On-demand AI suggestion generation for a specific field across the publisher's
    catalog. Called via POST /portal/suggestions/generate.

    Skips books that already have adequate content or a pending suggestion.
    Returns number of suggestions created.
    """
    from app.models.portal import BookDistributor

    config = _FIELD_CONFIG.get(field)
    if config is None:
        raise ValueError(f"Unsupported field: {field}")

    settings = get_settings()
    model_id = settings.bedrock_model_id
    region = settings.aws_region
    check_attr = config["check_attr"]
    thin_len = config["thin_len"]
    result_key = config["result_key"]

    # Fetch publisher's book IDs
    book_ids = list((await session.execute(
        select(BookDistributor.book_id)
        .where(BookDistributor.feed_source_id == feed_source_id)
        .distinct()
        .limit(limit * 3)  # over-fetch to account for skips
    )).scalars().all())

    if not book_ids:
        return 0

    created = 0

    for book_id in book_ids:
        if created >= limit:
            break
        try:
            book = (await session.execute(
                select(Book).where(Book.id == book_id)
            )).scalar_one_or_none()
            if book is None:
                continue

            # Skip if field is already adequate
            existing = getattr(book, check_attr, None) or ""
            if len(existing) >= thin_len:
                continue

            # Skip if pending suggestion already exists
            exists = (await session.execute(
                select(AiSuggestion.id).where(
                    AiSuggestion.book_id == book_id,
                    AiSuggestion.field_name == field,
                    AiSuggestion.status == "pending",
                )
            )).scalar_one_or_none()
            if exists is not None:
                continue

            # Load publisher, contributors, subjects
            publisher_name: str | None = None
            if book.publisher_id:
                pub = (await session.execute(
                    select(Publisher).where(Publisher.id == book.publisher_id)
                )).scalar_one_or_none()
                publisher_name = pub.name if pub else None

            contributors = list((await session.execute(
                select(BookContributor).where(BookContributor.book_id == book_id)
            )).scalars().all())
            subjects = list((await session.execute(
                select(BookSubject).where(BookSubject.book_id == book_id)
            )).scalars().all())

            contributor_names = [c.person_name for c in contributors if c.person_name]
            subject_headings = [s.subject_heading for s in subjects if s.subject_heading]

            # Build field-specific prompt
            if field == "description":
                prompt = _build_description_prompt(
                    title=book.title,
                    publisher_name=publisher_name,
                    product_form=book.product_form,
                    existing_description=existing or None,
                    contributor_names=contributor_names,
                    subject_headings=subject_headings,
                )
            elif field == "toc":
                prompt = _build_toc_prompt(
                    title=book.title,
                    description=book.description,
                    contributor_names=contributor_names,
                    subject_headings=subject_headings,
                )
            else:  # excerpt
                prompt = _build_excerpt_prompt(
                    title=book.title,
                    description=book.description,
                    contributor_names=contributor_names,
                    subject_headings=subject_headings,
                )

            ai_result = await asyncio.to_thread(_call_bedrock, model_id, region, prompt)
            suggested = ai_result.get(result_key, "").strip()
            confidence = ai_result.get("confidence", "low")
            reasoning = ai_result.get("reasoning", "")

            if not suggested or confidence not in ("high", "medium", "low"):
                logger.warning("Unexpected AI response for book %s field %s: %s", book_id, field, ai_result)
                continue

            if confidence == "high":
                status = "auto_accepted"
                await _apply_to_editorial_layer(session, book_id, field, suggested)
            else:
                status = "pending"

            session.add(AiSuggestion(
                book_id=book_id,
                field_name=field,
                original_value=existing or None,
                suggested_value=suggested,
                confidence=confidence,
                model_id=model_id,
                reasoning=reasoning,
                status=status,
            ))
            created += 1
            logger.info(
                "AI suggestion created for book %s field=%s confidence=%s status=%s",
                book_id, field, confidence, status,
            )

        except Exception as exc:
            logger.warning("AI generation failed for book %s field %s: %s", book_id, field, exc)

    return created
