"""
Bedrock AI enrichment service.

Called after portal ingest completes. Generates description suggestions for books
with missing or thin metadata. High-confidence suggestions are auto-accepted and
applied to the editorial layer immediately; medium/low are queued for human review.
"""
from __future__ import annotations

import asyncio
import json
import logging
import uuid

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


def _build_prompt(
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
            prompt = _build_prompt(
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
