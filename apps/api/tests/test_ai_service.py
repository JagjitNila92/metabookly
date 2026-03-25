"""Tests for the Bedrock AI enrichment service.

_call_bedrock (the synchronous boto3 call) is always patched so tests never
hit AWS. The patch replaces it at the module level so asyncio.to_thread picks
up the mock when it runs the function in the executor.
"""
import uuid
from unittest.mock import patch

import pytest
from sqlalchemy import select
from sqlalchemy.dialects.postgresql import insert as pg_insert

from app.models.book import Book
from app.models.portal import AiSuggestion, BookEditorialLayer
from app.services.ai_service import enrich_books_after_ingest

# ─── Mock Bedrock responses ───────────────────────────────────────────────────

_HIGH = {
    "description": (
        "A landmark debut novel that traces the hidden networks binding a city together. "
        "Part thriller, part meditation on infrastructure and power, it asks what we owe "
        "to the systems that sustain us — and what happens when they begin to fail."
    ),
    "confidence": "high",
    "reasoning": "Full contributor and subject metadata available.",
}

_MEDIUM = {
    "description": "A thought-provoking exploration of urban systems and their discontents.",
    "confidence": "medium",
    "reasoning": "Subject metadata available but no contributor details.",
}

_LOW = {
    "description": "A book about cities.",
    "confidence": "low",
    "reasoning": "Very limited metadata — title only.",
}


# ─── Helpers ──────────────────────────────────────────────────────────────────

async def _insert_book(
    session,
    isbn: str,
    description: str | None = None,
) -> uuid.UUID:
    result = await session.execute(
        pg_insert(Book)
        .values(
            isbn13=isbn,
            title=f"Test Book {isbn[-4:]}",
            product_form="BC",
            description=description,
        )
        .on_conflict_do_update(
            index_elements=["isbn13"],
            set_={"title": f"Test Book {isbn[-4:]}"},
        )
        .returning(Book.id)
    )
    await session.flush()
    return result.scalar_one()


def _patch_bedrock(return_value):
    """Context manager that replaces _call_bedrock with a synchronous stub."""
    return patch("app.services.ai_service._call_bedrock", return_value=return_value)


# ─── Tests ────────────────────────────────────────────────────────────────────

class TestEnrichBooksAfterIngest:
    async def test_empty_list_returns_zero(self, session):
        result = await enrich_books_after_ingest(session, [])
        assert result == 0

    async def test_adequate_description_is_skipped(self, session):
        """Books whose description is already >= 100 chars should not be enriched."""
        long_desc = "A" * 150
        book_id = await _insert_book(session, "9780099100001", description=long_desc)

        with _patch_bedrock(_HIGH) as mock:
            result = await enrich_books_after_ingest(session, [book_id])

        mock.assert_not_called()
        assert result == 0

    async def test_missing_description_triggers_enrichment(self, session):
        book_id = await _insert_book(session, "9780099100002", description=None)

        with _patch_bedrock(_MEDIUM):
            result = await enrich_books_after_ingest(session, [book_id])

        assert result == 1

    async def test_short_description_triggers_enrichment(self, session):
        book_id = await _insert_book(session, "9780099100003", description="Too short.")

        with _patch_bedrock(_MEDIUM):
            result = await enrich_books_after_ingest(session, [book_id])

        assert result == 1

    async def test_existing_pending_suggestion_blocks_enrichment(self, session):
        book_id = await _insert_book(session, "9780099100004", description=None)
        session.add(AiSuggestion(
            book_id=book_id,
            field_name="description",
            suggested_value="Already queued.",
            confidence="medium",
            status="pending",
        ))
        await session.flush()

        with _patch_bedrock(_MEDIUM) as mock:
            result = await enrich_books_after_ingest(session, [book_id])

        mock.assert_not_called()
        assert result == 0

    async def test_medium_confidence_creates_pending_suggestion(self, session):
        book_id = await _insert_book(session, "9780099100005", description=None)

        with _patch_bedrock(_MEDIUM):
            await enrich_books_after_ingest(session, [book_id])

        suggestion = (await session.execute(
            select(AiSuggestion).where(AiSuggestion.book_id == book_id)
        )).scalar_one()
        assert suggestion.status == "pending"
        assert suggestion.confidence == "medium"
        assert suggestion.field_name == "description"
        assert suggestion.suggested_value == _MEDIUM["description"]
        assert suggestion.reasoning == _MEDIUM["reasoning"]

    async def test_high_confidence_auto_accepts_suggestion(self, session):
        book_id = await _insert_book(session, "9780099100006", description=None)

        with _patch_bedrock(_HIGH):
            await enrich_books_after_ingest(session, [book_id])

        suggestion = (await session.execute(
            select(AiSuggestion).where(AiSuggestion.book_id == book_id)
        )).scalar_one()
        assert suggestion.status == "auto_accepted"
        assert suggestion.confidence == "high"

    async def test_high_confidence_applies_to_editorial_layer(self, session):
        book_id = await _insert_book(session, "9780099100007", description=None)

        with _patch_bedrock(_HIGH):
            await enrich_books_after_ingest(session, [book_id])

        layer = (await session.execute(
            select(BookEditorialLayer).where(BookEditorialLayer.book_id == book_id)
        )).scalar_one_or_none()
        assert layer is not None
        assert layer.description == _HIGH["description"]
        assert layer.field_sources.get("description") == "ai_accepted"

    async def test_low_confidence_creates_pending_suggestion(self, session):
        book_id = await _insert_book(session, "9780099100008", description=None)

        with _patch_bedrock(_LOW):
            await enrich_books_after_ingest(session, [book_id])

        suggestion = (await session.execute(
            select(AiSuggestion).where(AiSuggestion.book_id == book_id)
        )).scalar_one()
        assert suggestion.status == "pending"
        assert suggestion.confidence == "low"

    async def test_bedrock_error_is_swallowed(self, session):
        """A Bedrock failure must not propagate — ingest should never fail due to AI."""
        book_id = await _insert_book(session, "9780099100009", description=None)

        with patch(
            "app.services.ai_service._call_bedrock",
            side_effect=Exception("Bedrock unavailable"),
        ):
            result = await enrich_books_after_ingest(session, [book_id])

        assert result == 0  # no suggestions created, no exception raised

    async def test_invalid_confidence_value_skipped(self, session):
        book_id = await _insert_book(session, "9780099100010", description=None)
        bad_response = {
            "description": "Some description.",
            "confidence": "very_high",  # not a valid value
            "reasoning": "ok",
        }

        with _patch_bedrock(bad_response):
            result = await enrich_books_after_ingest(session, [book_id])

        assert result == 0

    async def test_multiple_books_processed(self, session):
        ids = []
        for i, isbn in enumerate(["9780099100011", "9780099100012", "9780099100013"]):
            ids.append(await _insert_book(session, isbn, description=None))

        with _patch_bedrock(_MEDIUM):
            result = await enrich_books_after_ingest(session, ids)

        assert result == 3

    async def test_original_value_stored_on_suggestion(self, session):
        short_desc = "Short."
        book_id = await _insert_book(session, "9780099100014", description=short_desc)

        with _patch_bedrock(_MEDIUM):
            await enrich_books_after_ingest(session, [book_id])

        suggestion = (await session.execute(
            select(AiSuggestion).where(AiSuggestion.book_id == book_id)
        )).scalar_one()
        assert suggestion.original_value == short_desc

    async def test_model_id_stored_on_suggestion(self, session):
        book_id = await _insert_book(session, "9780099100015", description=None)

        with _patch_bedrock(_MEDIUM):
            await enrich_books_after_ingest(session, [book_id])

        suggestion = (await session.execute(
            select(AiSuggestion).where(AiSuggestion.book_id == book_id)
        )).scalar_one()
        assert suggestion.model_id is not None
        assert "claude" in suggestion.model_id.lower()
