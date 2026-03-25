"""Tests for ONIX 2.1 and 3.0 parsers and the version dispatcher."""
from decimal import Decimal
from pathlib import Path

import pytest

from app.parsers import detect_onix_version, parse_onix_auto

FIXTURES = Path(__file__).parent / "fixtures"


def _load(name: str) -> bytes:
    return (FIXTURES / name).read_bytes()


# ─── Version detection ────────────────────────────────────────────────────────

class TestDetectOnixVersion:
    def test_detects_30_by_release_attr_double_quotes(self):
        xml = b'<ONIXMessage release="3.0" xmlns="http://ns.editeur.org/onix/3.0/reference">'
        assert detect_onix_version(xml) == "3.0"

    def test_detects_30_by_release_attr_single_quotes(self):
        xml = b"<ONIXMessage release='3.0'>"
        assert detect_onix_version(xml) == "3.0"

    def test_detects_30_by_namespace_uri(self):
        xml = b'<ONIXMessage xmlns="http://ns.editeur.org/onix/3.0/reference">'
        assert detect_onix_version(xml) == "3.0"

    def test_detects_21_by_release_attr(self):
        xml = b'<ONIXMessage release="2.1">'
        assert detect_onix_version(xml) == "2.1"

    def test_detects_21_by_namespace_uri(self):
        xml = b'<ONIXMessage xmlns="http://ns.editeur.org/onix/2.1/reference">'
        assert detect_onix_version(xml) == "2.1"

    def test_defaults_to_30_when_no_version_hint(self):
        xml = b'<ONIXMessage><Product></Product></ONIXMessage>'
        assert detect_onix_version(xml) == "3.0"

    def test_version_detection_is_case_insensitive(self):
        xml = b'<ONIXMessage RELEASE="3.0">'
        assert detect_onix_version(xml) == "3.0"


# ─── ONIX 3.0 parser ─────────────────────────────────────────────────────────

class TestOnix3Parser:
    def _books(self):
        version, it = parse_onix_auto(_load("sample_onix3.xml"))
        assert version == "3.0"
        return list(it)

    def test_correct_product_count(self):
        # Fixture: 6 products — 4 upserts + 1 delete + 1 advance notice (skipped by parser)
        books = self._books()
        assert len(books) == 5

    def test_advance_notice_skipped(self):
        isbns = [b.isbn13 for b in self._books()]
        assert "9780000999999" not in isbns  # NotificationType 01

    def test_basic_fields_book1(self):
        book = self._books()[0]
        assert book.isbn13 == "9781234567890"
        assert book.isbn10 == "1234567890"
        assert book.title == "The Midnight Algorithm"
        assert book.subtitle == "A Novel of Code and Consequence"
        assert book.notification_type == "03"
        assert book.product_form == "BC"
        assert book.product_form_detail == "B206"
        assert book.page_count == 352
        assert book.language_code == "eng"
        assert book.edition_number == 1

    def test_publisher_and_imprint(self):
        book = self._books()[0]
        assert book.publisher_name == "Sample Publisher Ltd"
        assert book.imprint_name == "Meridian Press"

    def test_contributors_book1(self):
        book = self._books()[0]
        assert len(book.contributors) == 2

        author = book.contributors[0]
        assert author.role_code == "A01"
        assert author.person_name == "Eleanor Voss"
        assert author.person_name_inverted == "Voss, Eleanor"
        assert "award-winning" in author.bio

        editor = book.contributors[1]
        assert editor.role_code == "B06"
        assert editor.person_name == "Marcus Webb"

    def test_subjects_book1(self):
        book = self._books()[0]
        assert len(book.subjects) == 3

        main = next(s for s in book.subjects if s.main_subject)
        assert main.scheme_id == "12"  # BIC
        assert main.subject_code == "FF"

        bisac = next(s for s in book.subjects if s.scheme_id == "10")
        assert "Science Fiction" in bisac.subject_heading

    def test_description_plain_text(self):
        book = self._books()[0]
        assert book.description is not None
        assert "data scientist Lena Park" in book.description
        assert "<" not in book.description  # HTML stripped

    def test_toc_extracted(self):
        book = self._books()[0]
        assert book.toc is not None
        assert "Part One" in book.toc

    def test_cover_image_largest_version(self):
        # Fixture book 1 has 300 and 600 dpi versions — should pick highest
        book = self._books()[0]
        assert book.cover_image_url is not None
        assert "600" in book.cover_image_url

    def test_uk_rights_gb_included_explicitly(self):
        book = self._books()[0]  # SalesRightsType=01 for GB IE
        assert book.uk_rights is True

    def test_uk_rights_world_region(self):
        book = self._books()[1]  # SalesRightsType=01 for WORLD
        assert book.uk_rights is True

    def test_uk_rights_europe_region(self):
        book = self._books()[2]  # SalesRightsType=02 for EUROPE
        assert book.uk_rights is True

    def test_uk_rights_none_when_unspecified(self):
        # Book 4 in fixture has no SalesRights
        book = self._books()[3]
        # Either None or True is acceptable since no rights = unknown;
        # just confirm it doesn't erroneously return False
        assert book.uk_rights is not False

    def test_rrp_gbp_extraction(self):
        book = self._books()[0]
        assert book.rrp_gbp == Decimal("14.99")

    def test_rrp_gbp_and_usd(self):
        book = self._books()[1]
        assert book.rrp_gbp == Decimal("22.99")
        assert book.rrp_usd == Decimal("28.00")

    def test_html_description_stripped(self):
        book = self._books()[1]  # Has CDATA HTML description
        assert "<p>" not in book.description
        assert "Fifteenth-century Timbuktu" in book.description

    def test_publication_date_parsed(self):
        from datetime import date
        book = self._books()[0]
        assert book.publication_date == date(2024, 3, 15)

    def test_delete_notification(self):
        # SP-005 is NotificationType 05, appears before the skipped advance notice
        delete_books = [b for b in self._books() if b.notification_type == "05"]
        assert len(delete_books) == 1
        assert delete_books[0].isbn13 == "9780000000001"


# ─── ONIX 2.1 parser ─────────────────────────────────────────────────────────

class TestOnix21Parser:
    def _books(self):
        version, it = parse_onix_auto(_load("sample_onix21.xml"))
        assert version == "2.1"
        return list(it)

    def test_correct_product_count(self):
        # Fixture: 2 upserts + 1 delete = 3 ParsedBooks
        books = self._books()
        assert len(books) == 3

    def test_basic_fields(self):
        book = self._books()[0]
        assert book.isbn13 == "9781234500021"
        assert book.isbn10 == "1234500021"
        assert book.title == "The Fens in Winter"
        assert book.subtitle == "A Norfolk Mystery"
        assert book.notification_type == "03"
        assert book.product_form == "BC"
        assert book.language_code == "eng"

    def test_number_of_pages(self):
        book = self._books()[0]
        assert book.page_count == 288

    def test_othertext_main_description(self):
        book = self._books()[0]
        assert book.description is not None
        assert "Inspector Rhys Cole" in book.description

    def test_othertext_toc(self):
        book = self._books()[0]
        assert book.toc is not None
        assert "Part One" in book.toc

    def test_othertext_short_annotation_fallback(self):
        # Book 2 in fixture has only TextTypeCode 02 (short annotation)
        book = self._books()[1]
        assert book.description is not None
        assert "fallback" in book.description

    def test_contributor_parsed(self):
        book = self._books()[0]
        assert len(book.contributors) == 1
        c = book.contributors[0]
        assert c.person_name == "Dorothy Marsh"
        assert c.person_name_inverted == "Marsh, Dorothy"
        assert c.role_code == "A01"

    def test_basic_main_subject(self):
        # BASICMainSubject should be treated as main subject with BIC scheme
        book = self._books()[0]
        main = next((s for s in book.subjects if s.main_subject), None)
        assert main is not None
        assert main.scheme_id == "12"  # BIC
        assert main.subject_code == "FF"

    def test_mediafile_cover(self):
        book = self._books()[0]
        assert book.cover_image_url is not None
        assert "9781234500021" in book.cover_image_url

    def test_uk_rights_from_rights_territory(self):
        book = self._books()[0]
        assert book.uk_rights is True  # GB IE in RightsTerritory

    def test_rrp_from_supply_detail(self):
        book = self._books()[0]
        assert book.rrp_gbp == Decimal("12.99")

    def test_publisher_name(self):
        book = self._books()[0]
        assert book.publisher_name == "Sample Publisher 2.1 Ltd"
        assert book.imprint_name == "Meridian Crime"

    def test_delete_notification(self):
        delete_book = self._books()[-1]
        assert delete_book.notification_type == "05"
        assert delete_book.isbn13 == "9781234500099"


# ─── Dispatcher (parse_onix_auto) ────────────────────────────────────────────

class TestDispatcher:
    def test_routes_30_file_correctly(self):
        version, books = parse_onix_auto(_load("sample_onix3.xml"))
        assert version == "3.0"
        assert next(books).isbn13 == "9781234567890"

    def test_routes_21_file_correctly(self):
        version, books = parse_onix_auto(_load("sample_onix21.xml"))
        assert version == "2.1"
        assert next(books).isbn13 == "9781234500021"

    def test_accepts_bytes_input(self):
        content = _load("sample_onix3.xml")
        assert isinstance(content, bytes)
        version, _ = parse_onix_auto(content)
        assert version == "3.0"
