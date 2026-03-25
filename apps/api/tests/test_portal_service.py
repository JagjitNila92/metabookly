"""Tests for the portal ingest service.

Uses a real PostgreSQL DB with rolled-back transactions (see conftest.py).
All ISBNs in this file use the 978-0-00-0XX-XXXX range to avoid collisions
with seed data or other test files.
"""
import uuid

import pytest
from sqlalchemy import select, text

from app.models.book import Book
from app.models.portal import (
    AiSuggestion,
    BookEditorialLayer,
    FeedSource,
    MetadataConflict,
    OnixFeedV2,
)
from app.services.portal_service import ingest_onix_portal


# ─── Helpers ─────────────────────────────────────────────────────────────────

def _onix_feed(
    isbn: str,
    description: str | None = None,
    notification_type: str = "03",
) -> bytes:
    """Build a minimal valid ONIX 3.0 feed with a single product."""
    desc_xml = ""
    if description:
        desc_xml = f"""
    <CollateralDetail>
      <TextContent>
        <TextType>03</TextType>
        <ContentAudience>00</ContentAudience>
        <Text textformat="06">{description}</Text>
      </TextContent>
    </CollateralDetail>"""

    return f"""<?xml version="1.0" encoding="UTF-8"?>
<ONIXMessage release="3.0" xmlns="http://ns.editeur.org/onix/3.0/reference">
  <Header>
    <Sender><SenderName>Test</SenderName></Sender>
    <SentDateTime>20260101</SentDateTime>
  </Header>
  <Product>
    <RecordReference>TEST-{isbn}</RecordReference>
    <NotificationType>{notification_type}</NotificationType>
    <ProductIdentifier>
      <ProductIDType>15</ProductIDType>
      <IDValue>{isbn}</IDValue>
    </ProductIdentifier>
    <DescriptiveDetail>
      <ProductComposition>00</ProductComposition>
      <ProductForm>BC</ProductForm>
      <TitleDetail>
        <TitleType>01</TitleType>
        <TitleElement>
          <TitleElementLevel>01</TitleElementLevel>
          <TitleText>Test Book {isbn[-4:]}</TitleText>
        </TitleElement>
      </TitleDetail>
      <Contributor>
        <SequenceNumber>1</SequenceNumber>
        <ContributorRole>A01</ContributorRole>
        <PersonName>Test Author</PersonName>
      </Contributor>
      <Language>
        <LanguageRole>01</LanguageRole>
        <LanguageCode>eng</LanguageCode>
      </Language>
    </DescriptiveDetail>
    {desc_xml}
    <PublishingDetail>
      <Publisher>
        <PublishingRole>01</PublishingRole>
        <PublisherName>Test Publisher</PublisherName>
      </Publisher>
      <PublishingStatus>04</PublishingStatus>
    </PublishingDetail>
    <ProductSupply>
      <SupplyDetail>
        <Supplier>
          <SupplierRole>01</SupplierRole>
          <SupplierName>Test</SupplierName>
        </Supplier>
        <SupplyToTerritory>
          <RegionsIncluded>WORLD</RegionsIncluded>
        </SupplyToTerritory>
        <ProductAvailability>20</ProductAvailability>
      </SupplyDetail>
    </ProductSupply>
  </Product>
</ONIXMessage>""".encode()


async def _ingest(
    session,
    isbn: str,
    description: str | None = None,
    notification_type: str = "03",
    feed_source_id: uuid.UUID | None = None,
    sequence_number: int | None = None,
) -> dict:
    return await ingest_onix_portal(
        session,
        _onix_feed(isbn, description, notification_type),
        s3_bucket="test-bucket",
        s3_key=f"test/{isbn}.xml",
        feed_source_id=feed_source_id,
        sequence_number=sequence_number,
        triggered_by="test",
    )


async def _make_feed_source(session) -> uuid.UUID:
    fs = FeedSource(name="Test Publisher", source_type="publisher", priority=30)
    session.add(fs)
    await session.flush()
    return fs.id


# ─── Basic ingest ─────────────────────────────────────────────────────────────

class TestBasicIngest:
    async def test_upserts_book_to_db(self, session):
        result = await _ingest(session, "9780000010001")

        assert result["status"] == "completed"
        assert result["records_upserted"] == 1
        assert result["records_failed"] == 0

        book = (await session.execute(
            select(Book).where(Book.isbn13 == "9780000010001")
        )).scalar_one_or_none()
        assert book is not None
        assert "0001" in book.title

    async def test_creates_feed_record(self, session):
        result = await _ingest(session, "9780000010002")

        feed = (await session.execute(
            select(OnixFeedV2).where(OnixFeedV2.id == uuid.UUID(result["feed_id"]))
        )).scalar_one_or_none()

        assert feed is not None
        assert feed.status == "completed"
        assert feed.records_upserted == 1
        assert feed.onix_version == "3.0"
        assert feed.s3_bucket == "test-bucket"

    async def test_description_stored_on_book(self, session):
        desc = "A perfectly adequate test description for this book."
        await _ingest(session, "9780000010003", description=desc)

        book = (await session.execute(
            select(Book).where(Book.isbn13 == "9780000010003")
        )).scalar_one()
        assert book.description == desc

    async def test_second_ingest_is_idempotent(self, session):
        """Re-ingesting the same ISBN updates ONIX-locked fields but not description.
        Description is an editorial field and is only set on initial insert via the
        portal pipeline — updates go through the editorial layer conflict flow."""
        await _ingest(session, "9780000010004", description="Original.")
        await _ingest(session, "9780000010004", description="Updated by second feed.")

        book = (await session.execute(
            select(Book).where(Book.isbn13 == "9780000010004")
        )).scalar_one()
        # Description stays as set on initial insert — ONIX re-ingests don't overwrite it
        assert book.description == "Original."

    async def test_summary_fields_present(self, session):
        result = await _ingest(session, "9780000010005")
        assert "feed_id" in result
        assert "onix_version" in result
        assert "records_found" in result
        assert result["gaps_detected"] is False


# ─── NotificationType handling ────────────────────────────────────────────────

class TestNotificationTypes:
    async def test_soft_delete_sets_out_of_print(self, session):
        # Ingest the book first
        await _ingest(session, "9780000020001", description="Will be deleted.")

        book = (await session.execute(
            select(Book).where(Book.isbn13 == "9780000020001")
        )).scalar_one()
        assert book.out_of_print is not True

        # Send delete notification
        result = await _ingest(session, "9780000020001", notification_type="05")
        assert result["status"] == "completed"

        await session.refresh(book)
        assert book.out_of_print is True

    async def test_soft_delete_does_not_remove_row(self, session):
        await _ingest(session, "9780000020002")
        await _ingest(session, "9780000020002", notification_type="05")

        book = (await session.execute(
            select(Book).where(Book.isbn13 == "9780000020002")
        )).scalar_one_or_none()
        assert book is not None  # row still exists


# ─── Editorial layer protection ───────────────────────────────────────────────

class TestEditorialLayerProtection:
    async def test_conflict_created_when_editorial_description_differs(self, session):
        isbn = "9780000030001"
        await _ingest(session, isbn, description="Publisher's original description text.")

        book = (await session.execute(
            select(Book).where(Book.isbn13 == isbn)
        )).scalar_one()

        # Mark description as editorially modified
        session.add(BookEditorialLayer(
            book_id=book.id,
            description="Our editorial version — manually curated.",
            field_sources={"description": "editorial"},
            edited_by="test-admin",
        ))
        await session.flush()

        result = await _ingest(session, isbn, description="A different ONIX description now.")
        assert result["records_conflicted"] == 1

        conflict = (await session.execute(
            select(MetadataConflict).where(
                MetadataConflict.book_id == book.id,
                MetadataConflict.field_name == "description",
                MetadataConflict.status == "pending",
            )
        )).scalar_one_or_none()
        assert conflict is not None
        assert conflict.onix_value == "A different ONIX description now."
        assert conflict.editorial_value == "Our editorial version — manually curated."

    async def test_no_conflict_when_values_match(self, session):
        isbn = "9780000030002"
        shared_desc = "The exact same description in both ONIX and the editorial layer."
        await _ingest(session, isbn, description=shared_desc)

        book = (await session.execute(
            select(Book).where(Book.isbn13 == isbn)
        )).scalar_one()

        session.add(BookEditorialLayer(
            book_id=book.id,
            description=shared_desc,
            field_sources={"description": "editorial"},
            edited_by="test-admin",
        ))
        await session.flush()

        result = await _ingest(session, isbn, description=shared_desc)
        assert result["records_conflicted"] == 0

    async def test_conflict_not_duplicated_on_repeated_ingests(self, session):
        """Two feeds both trying to update the same protected field → only one pending conflict."""
        isbn = "9780000030003"
        await _ingest(session, isbn, description="Short.")

        book = (await session.execute(
            select(Book).where(Book.isbn13 == isbn)
        )).scalar_one()
        session.add(BookEditorialLayer(
            book_id=book.id,
            description="Editorial version.",
            field_sources={"description": "editorial"},
            edited_by="test",
        ))
        await session.flush()

        await _ingest(session, isbn, description="ONIX update one.")
        await _ingest(session, isbn, description="ONIX update two.")

        count = (await session.execute(
            text("SELECT COUNT(*) FROM metadata_conflicts WHERE book_id = :bid AND status = 'pending'")
            .bindparams(bid=book.id)
        )).scalar_one()
        assert count == 1

    async def test_ai_accepted_field_also_protected(self, session):
        """Fields marked ai_accepted are treated the same as editorial."""
        isbn = "9780000030004"
        await _ingest(session, isbn, description=None)

        book = (await session.execute(
            select(Book).where(Book.isbn13 == isbn)
        )).scalar_one()
        session.add(BookEditorialLayer(
            book_id=book.id,
            description="AI-generated description that was accepted.",
            field_sources={"description": "ai_accepted"},
            edited_by=None,
        ))
        await session.flush()

        result = await _ingest(session, isbn, description="New ONIX description.")
        assert result["records_conflicted"] == 1


# ─── Sequence / gap detection ─────────────────────────────────────────────────

class TestSequenceTracking:
    async def test_no_gap_when_sequential(self, session):
        fs_id = await _make_feed_source(session)
        isbn = "9780000040001"

        r1 = await _ingest(session, isbn, feed_source_id=fs_id, sequence_number=1)
        assert not r1["gaps_detected"]

        r2 = await _ingest(session, isbn, feed_source_id=fs_id, sequence_number=2)
        assert not r2["gaps_detected"]

    async def test_gap_flagged_when_sequence_jumps(self, session):
        fs_id = await _make_feed_source(session)
        isbn = "9780000040002"

        await _ingest(session, isbn, feed_source_id=fs_id, sequence_number=1)
        result = await _ingest(session, isbn, feed_source_id=fs_id, sequence_number=5)

        assert result["gaps_detected"] is True

    async def test_no_gap_check_without_sequence_number(self, session):
        fs_id = await _make_feed_source(session)
        isbn = "9780000040003"

        # Feeds without sequence numbers should never flag a gap
        r = await _ingest(session, isbn, feed_source_id=fs_id, sequence_number=None)
        assert not r["gaps_detected"]

    async def test_gap_recorded_in_feed_row(self, session):
        fs_id = await _make_feed_source(session)
        isbn = "9780000040004"

        await _ingest(session, isbn, feed_source_id=fs_id, sequence_number=1)
        result = await _ingest(session, isbn, feed_source_id=fs_id, sequence_number=10)

        feed = (await session.execute(
            select(OnixFeedV2).where(OnixFeedV2.id == uuid.UUID(result["feed_id"]))
        )).scalar_one()
        assert feed.gaps_detected is True
        assert feed.expected_sequence == 2
        assert feed.sequence_number == 10


# ─── Error resilience ─────────────────────────────────────────────────────────

class TestErrorResilience:
    async def test_malformed_xml_does_not_raise(self, session):
        """Malformed XML should never crash the caller — lxml may yield nothing or fail."""
        result = await ingest_onix_portal(
            session,
            b"<not valid xml at all!!!",
            s3_bucket="test-bucket",
            s3_key="test/bad.xml",
            triggered_by="test",
        )
        # Status is either "completed" (lxml silently yields nothing) or "failed"
        assert result["status"] in ("completed", "failed")
        assert result["records_upserted"] == 0

    async def test_empty_feed_completes_with_zero_records(self, session):
        empty = b"""<?xml version="1.0" encoding="UTF-8"?>
<ONIXMessage release="3.0" xmlns="http://ns.editeur.org/onix/3.0/reference">
  <Header><Sender><SenderName>Test</SenderName></Sender><SentDateTime>20260101</SentDateTime></Header>
</ONIXMessage>"""
        result = await ingest_onix_portal(
            session,
            empty,
            s3_bucket="test-bucket",
            s3_key="test/empty.xml",
            triggered_by="test",
        )
        assert result["status"] == "completed"
        assert result["records_found"] == 0
        assert result["records_upserted"] == 0
