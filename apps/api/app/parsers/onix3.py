"""ONIX 3.0 streaming XML parser.

Uses lxml iterparse to process one <Product> at a time — memory-bounded for
large distributor feeds (can be 100MB+).

Reference codelist: https://ns.editeur.org/onix/en/
Only reference tag names are supported (not short/numeric tags).

What we extract
───────────────
  Book identity:    ISBN-13, ISBN-10
  Title:            TitleDetail[TitleType=01]
  Contributors:     all roles, with display + inverted names, bio
  Publisher:        PublishingDetail/Publisher[PublishingRole=01]
  Imprint:          PublishingDetail/Imprint
  Format:           ProductForm, ProductFormDetail, edition, language, pages
  Content:          description (03), short desc (02), TOC (04), excerpt (23)
  Cover:            SupportingResource[ContentType=01][Mode=03] — largest version
  Subjects:         BIC/BISAC/Thema, main-subject flag
  Audience:         ONIX audience code
  Publishing:       status, publication date, out-of-print flag
  UK rights:        distilled from SalesRights territory logic (True/False/None)
  RRP:              GBP + USD list price from ProductSupply (NOT trade price)

What we skip
────────────
  Advance notices (NotificationType 01/02)
  ProductAvailability / stock levels (comes from distributor APIs per retailer)
  Physical dimensions (thickness, weight only — height + width are extracted)
  Prize / award records
  Related products
  Detailed tax splits in pricing
  Supply chain / supplier names
"""
from __future__ import annotations

import re
from dataclasses import dataclass, field
from datetime import date
from decimal import Decimal, InvalidOperation
from io import BytesIO
from pathlib import Path
from typing import IO, Iterator

from lxml import etree
from lxml import html as lxml_html


# Regions (ONIX list 49) that include Great Britain for sales-rights purposes.
_REGIONS_INCL_GB = frozenset({"WORLD", "EUROPE", "EUROZ"})


# ─── Parsed data containers ───────────────────────────────────────────────────

@dataclass
class ParsedContributor:
    sequence_number: int
    role_code: str          # e.g. "A01" = author, "B01" = editor
    person_name: str        # display name: "John Smith"
    person_name_inverted: str | None  # "Smith, John"
    bio: str | None


@dataclass
class ParsedSubject:
    scheme_id: str          # "10"=BISAC, "12"=BIC, "93"=Thema, "20"=keywords
    subject_code: str
    subject_heading: str | None
    main_subject: bool      # True if <MainSubject/> is present


@dataclass
class ParsedBook:
    # ── identity ────────────────────────────────────────────────────────────
    record_ref: str
    notification_type: str  # "03"=confirm/upsert  "05"=delete record
    isbn13: str
    isbn10: str | None = None

    # ── title ───────────────────────────────────────────────────────────────
    title: str = ""
    subtitle: str | None = None

    # ── publisher ───────────────────────────────────────────────────────────
    publisher_name: str | None = None
    imprint_name: str | None = None

    # ── format ──────────────────────────────────────────────────────────────
    product_form: str = "BA"            # BA=book (generic), BC=paperback, BB=hardback, DG=ebook
    product_form_detail: str | None = None
    edition_number: int | None = None
    edition_statement: str | None = None
    language_code: str = "eng"
    page_count: int | None = None

    # ── content ─────────────────────────────────────────────────────────────
    description: str | None = None      # HTML stripped to plain text
    toc: str | None = None
    excerpt: str | None = None

    # ── classification ──────────────────────────────────────────────────────
    audience_code: str | None = None    # ONIX list 28: "01"=general, "05"=children, etc.

    # ── dates & status ──────────────────────────────────────────────────────
    publication_date: date | None = None
    publishing_status: str | None = None  # raw ONIX code: "04"=active, "02"=forthcoming, "06"=OOP
    out_of_print: bool = False

    # ── rights & pricing ────────────────────────────────────────────────────
    # uk_rights: True=can sell in UK, False=cannot, None=not stated (assume yes)
    uk_rights: bool | None = None
    rrp_gbp: Decimal | None = None      # publisher list price, inc tax (reference only)
    rrp_usd: Decimal | None = None

    # ── dimensions ──────────────────────────────────────────────────────────
    height_mm: int | None = None            # ONIX MeasureType 01
    width_mm: int | None = None             # ONIX MeasureType 02

    # ── cover ───────────────────────────────────────────────────────────────
    cover_image_url: str | None = None

    # ── relations ───────────────────────────────────────────────────────────
    contributors: list[ParsedContributor] = field(default_factory=list)
    subjects: list[ParsedSubject] = field(default_factory=list)


# ─── Namespace-agnostic XML helpers ──────────────────────────────────────────

def _local(el) -> str:
    """
    Strip Clark-notation namespace from element tag.
    Returns "" for lxml comment/PI nodes whose .tag is a callable.
    """
    tag = el.tag
    if callable(tag):   # lxml comment, PI, or entity node
        return ""
    return tag.split('}', 1)[1] if '}' in tag else tag


def _find(parent, *path: str):
    """First nested element matching a sequence of local names."""
    el = parent
    for name in path:
        found = next((c for c in el if _local(c) == name), None)
        if found is None:
            return None
        el = found
    return el


def _findall(parent, name: str) -> list:
    """All direct children matching a local name."""
    return [c for c in parent if _local(c) == name]


def _text(parent, *path: str) -> str | None:
    """Text content of the first element matching path, stripped."""
    el = _find(parent, *path)
    return el.text.strip() if el is not None and el.text else None


# ─── Text cleaning ────────────────────────────────────────────────────────────

def _strip_html(raw: str) -> str:
    """
    Strip HTML tags from ONIX text content.
    Converts block-level elements to newlines first so paragraphs don't merge.
    """
    try:
        # Block closers → newline before stripping tags
        raw = re.sub(r'</(?:p|div|br|li|tr|h[1-6])[^>]*>', '\n', raw, flags=re.I)
        return lxml_html.fromstring(raw).text_content().strip()
    except Exception:
        return re.sub(r'<[^>]+>', ' ', raw).strip()


# ─── Field parsers ────────────────────────────────────────────────────────────

def _parse_date(raw: str) -> date | None:
    """Parse ONIX date: YYYYMMDD, YYYYMM, or YYYY."""
    raw = raw.strip()
    try:
        if len(raw) == 8:
            return date(int(raw[:4]), int(raw[4:6]), int(raw[6:]))
        if len(raw) == 6:
            return date(int(raw[:4]), int(raw[4:6]), 1)
        if len(raw) == 4:
            return date(int(raw), 1, 1)
    except (ValueError, TypeError):
        pass
    return None


def _territory_includes_gb(territory_el) -> bool:
    """
    Return True if a <Territory> element covers Great Britain.

    Handles the combinations:
      RegionsIncluded WORLD/EUROPE     → includes GB (unless excluded)
      CountriesIncluded GB             → explicit inclusion
      CountriesExcluded GB             → explicit exclusion (takes precedence)
      territory_el is None             → no restriction → True (worldwide)
    """
    if territory_el is None:
        return True  # no territory restriction = worldwide

    countries_ex = (_text(territory_el, "CountriesExcluded") or "").split()
    regions_ex = (_text(territory_el, "RegionsExcluded") or "").split()

    # Explicit exclusions take precedence
    if "GB" in countries_ex:
        return False
    if any(r in _REGIONS_INCL_GB for r in regions_ex):
        return False

    countries_in = (_text(territory_el, "CountriesIncluded") or "").split()
    regions_in = (_text(territory_el, "RegionsIncluded") or "").split()

    if "GB" in countries_in:
        return True
    if any(r in _REGIONS_INCL_GB for r in regions_in):
        return True

    # There is a Territory element but it doesn't mention GB at all.
    # This means some other explicit territory — GB is not included.
    return False


def _to_mm(value: float, unit: str) -> int:
    """Convert an ONIX Measurement value to whole millimetres.

    MeasureUnit codes (ONIX list 50):
      01 = centimetres   02 = inches   03 = millimetres
    """
    if unit == "01":    # cm → mm
        return round(value * 10)
    if unit == "02":    # inches → mm
        return round(value * 25.4)
    return round(value)  # 03=mm or anything else


# ─── Section parsers ─────────────────────────────────────────────────────────

def _parse_identifiers(product_el) -> tuple[str | None, str | None]:
    """Return (isbn13, isbn10)."""
    isbn13 = isbn10 = None
    for pid in _findall(product_el, "ProductIdentifier"):
        id_type = _text(pid, "ProductIDType")
        value = (_text(pid, "IDValue") or "").replace("-", "").replace(" ", "")
        if not value:
            continue
        if id_type == "15":
            isbn13 = value
        elif id_type == "02":
            isbn10 = value
    return isbn13, isbn10


def _parse_descriptive(product_el) -> dict:
    """Parse DescriptiveDetail: format, title, contributors, subjects, audience."""
    dd = _find(product_el, "DescriptiveDetail")
    out: dict = {
        "product_form": "BA",
        "product_form_detail": None,
        "edition_number": None,
        "edition_statement": None,
        "language_code": "eng",
        "page_count": None,
        "height_mm": None,
        "width_mm": None,
        "title": "",
        "subtitle": None,
        "audience_code": None,
        "contributors": [],
        "subjects": [],
    }
    if dd is None:
        return out

    out["product_form"] = _text(dd, "ProductForm") or "BA"
    out["product_form_detail"] = _text(dd, "ProductFormDetail")
    out["edition_statement"] = _text(dd, "EditionStatement")

    en = _text(dd, "EditionNumber")
    if en and en.isdigit():
        out["edition_number"] = int(en)

    # Language of text (LanguageRole 01)
    for lang_el in _findall(dd, "Language"):
        if _text(lang_el, "LanguageRole") == "01":
            code = _text(lang_el, "LanguageCode")
            if code:
                out["language_code"] = code
            break

    # Page count (ExtentType 00=main content, 08=total pages; ExtentUnit 03=pages)
    for extent_el in _findall(dd, "Extent"):
        if _text(extent_el, "ExtentType") in ("00", "08") and _text(extent_el, "ExtentUnit") == "03":
            val = _text(extent_el, "ExtentValue") or ""
            if val.isdigit():
                out["page_count"] = int(val)
            break

    # Physical dimensions (MeasureType: 01=height, 02=width; MeasureUnit: 01=cm, 02=in, 03=mm)
    for measure_el in _findall(dd, "Measure"):
        measure_type = _text(measure_el, "MeasureType")
        if measure_type not in ("01", "02"):
            continue
        val_str = _text(measure_el, "Measurement") or ""
        unit = _text(measure_el, "MeasureUnit") or "03"
        try:
            mm = _to_mm(float(val_str), unit)
        except (ValueError, TypeError):
            continue
        if measure_type == "01":
            out["height_mm"] = mm
        else:
            out["width_mm"] = mm

    # Distinctive/cover title (TitleType 01)
    for td in _findall(dd, "TitleDetail"):
        if _text(td, "TitleType") == "01":
            te = _find(td, "TitleElement")
            if te is not None:
                out["title"] = _text(te, "TitleText") or ""
                out["subtitle"] = _text(te, "Subtitle")
            break

    # Contributors
    contributors: list[ParsedContributor] = []
    for contrib_el in _findall(dd, "Contributor"):
        role = _text(contrib_el, "ContributorRole")
        if not role:
            continue

        # Prefer PersonName; fall back to KeyNames + NamesBeforeKey
        person_name = _text(contrib_el, "PersonName")
        keys = _text(contrib_el, "KeyNames")
        before = _text(contrib_el, "NamesBeforeKey")
        if not person_name:
            if keys and before:
                person_name = f"{before} {keys}"
            elif keys:
                person_name = keys
            else:
                continue  # cannot build a name

        # Inverted name for sorting ("Smith, John")
        inverted = _text(contrib_el, "PersonNameInverted")
        if not inverted and keys:
            inverted = f"{keys}, {before}" if before else keys

        bio_raw = _text(contrib_el, "BiographicalNote")
        bio = _strip_html(bio_raw) if bio_raw else None

        seq = _text(contrib_el, "SequenceNumber")
        contributors.append(ParsedContributor(
            sequence_number=int(seq) if seq and seq.isdigit() else len(contributors) + 1,
            role_code=role,
            person_name=person_name,
            person_name_inverted=inverted,
            bio=bio,
        ))
    out["contributors"] = contributors

    # Subjects (BIC=12, BISAC=10, Thema=93, keywords=20)
    subjects: list[ParsedSubject] = []
    for subj_el in _findall(dd, "Subject"):
        scheme = _text(subj_el, "SubjectSchemeIdentifier")
        code = _text(subj_el, "SubjectCode")
        if not scheme or not code:
            continue
        heading = _text(subj_el, "SubjectHeadingText")
        is_main = _find(subj_el, "MainSubject") is not None
        subjects.append(ParsedSubject(
            scheme_id=scheme,
            subject_code=code,
            subject_heading=heading,
            main_subject=is_main,
        ))
    out["subjects"] = subjects

    # Audience code (AudienceCodeType 01 = ONIX list 28)
    for aud_el in _findall(dd, "Audience"):
        if _text(aud_el, "AudienceCodeType") == "01":
            out["audience_code"] = _text(aud_el, "AudienceCodeValue")
            break

    return out


def _parse_collateral(product_el) -> dict:
    """Parse CollateralDetail: description, TOC, excerpt, cover image URL."""
    cd = _find(product_el, "CollateralDetail")
    out: dict = {"description": None, "toc": None, "excerpt": None, "cover_image_url": None}
    if cd is None:
        return out

    # TextType: 02=short description, 03=full description, 04=TOC, 23=excerpt/sample
    for tc in _findall(cd, "TextContent"):
        text_type = _text(tc, "TextType")
        raw = _text(tc, "Text")
        if not raw:
            continue

        # textformat attribute: "02"=HTML, "06"=plain text (default plain)
        text_el = _find(tc, "Text")
        fmt = text_el.get("textformat", "06") if text_el is not None else "06"
        clean = _strip_html(raw) if fmt == "02" else raw.strip()

        if text_type == "03" and out["description"] is None:
            out["description"] = clean
        elif text_type == "02" and out["description"] is None:
            # Short description as fallback when no full description present
            out["description"] = clean
        elif text_type == "04" and out["toc"] is None:
            out["toc"] = clean
        elif text_type == "23" and out["excerpt"] is None:
            out["excerpt"] = clean

    # Cover image — ResourceContentType 01=front cover, ResourceMode 03=image
    # Pick the largest version (by pixel width feature) if multiple exist.
    best_url: str | None = None
    best_width = -1
    for sr in _findall(cd, "SupportingResource"):
        if _text(sr, "ResourceContentType") != "01":
            continue
        if _text(sr, "ResourceMode") != "03":
            continue
        for rv in _findall(sr, "ResourceVersion"):
            url = _text(rv, "ResourceLink")
            if not url:
                continue
            width = 0
            for rvf in _findall(rv, "ResourceVersionFeature"):
                # FeatureType 01 = image pixel width
                if _text(rvf, "ResourceVersionFeatureType") == "01":
                    w_str = _text(rvf, "FeatureValue") or "0"
                    width = int(w_str) if w_str.isdigit() else 0
            if width > best_width:
                best_width = width
                best_url = url

    out["cover_image_url"] = best_url
    return out


def _parse_publishing(product_el) -> dict:
    """
    Parse PublishingDetail: publisher, imprint, status, publication date,
    and UK sales rights.

    Sales rights logic
    ──────────────────
    ONIX can have multiple SalesRights blocks (e.g. "exclusive in GB",
    "non-exclusive in WORLD"). We distil them to a single uk_rights boolean:

      Any "for sale" right (type 01/02/06) covering GB → uk_rights = True
      "Not for sale" (type 03) covering GB             → uk_rights = False
      "For sale" takes precedence over "not for sale"   if both are present
      No SalesRights at all                            → uk_rights = None
        (the ingestion service treats None as "assume yes" for UK publishers)
    """
    pd = _find(product_el, "PublishingDetail")
    out: dict = {
        "publisher_name": None,
        "imprint_name": None,
        "publishing_status": None,
        "out_of_print": False,
        "publication_date": None,
        "uk_rights": None,
    }
    if pd is None:
        return out

    # Publisher (PublishingRole 01 = publisher)
    for pub_el in _findall(pd, "Publisher"):
        if _text(pub_el, "PublishingRole") == "01":
            out["publisher_name"] = _text(pub_el, "PublisherName")
            break

    # Imprint
    imprint_el = _find(pd, "Imprint")
    if imprint_el is not None:
        out["imprint_name"] = _text(imprint_el, "ImprintName")

    # Publishing status
    status = _text(pd, "PublishingStatus")
    out["publishing_status"] = status
    # 06=OOP, 07=recalled, 11=withdrawn from sale, 12=not listed
    out["out_of_print"] = status in ("06", "07", "11", "12")

    # Publication date (PublishingDateRole 01 = publication date)
    for pdate_el in _findall(pd, "PublishingDate"):
        if _text(pdate_el, "PublishingDateRole") == "01":
            raw = _text(pdate_el, "Date")
            if raw:
                out["publication_date"] = _parse_date(raw)
            break

    # Sales rights → uk_rights boolean
    for_sale_in_gb = False
    not_for_sale_in_gb = False
    for sr_el in _findall(pd, "SalesRights"):
        sr_type = _text(sr_el, "SalesRightsType")
        covers_gb = _territory_includes_gb(_find(sr_el, "Territory"))
        if sr_type in ("01", "02", "06"):   # exclusive / non-exclusive / mixed for sale
            if covers_gb:
                for_sale_in_gb = True
        elif sr_type == "03":               # not for sale
            if covers_gb:
                not_for_sale_in_gb = True

    if for_sale_in_gb:
        out["uk_rights"] = True
    elif not_for_sale_in_gb:
        out["uk_rights"] = False
    # else: None — not stated

    return out


def _parse_supply(product_el) -> dict:
    """
    Extract publisher RRP (list/cover price) from ProductSupply.

    Important: this is the publisher's recommended retail price, used as
    reference data on the book record. It is NOT the trade price a retailer
    pays — that comes from distributor APIs per retailer account.

    Priority: PriceType 02 (RRP inc tax) over 01 (exc tax)
    Territory scoring: GB-specific (score 2) > WORLD (score 1) > unspecified (score 0)
    """
    out: dict = {"rrp_gbp": None, "rrp_usd": None}
    # (currency, price_type) → (amount, territory_score)
    candidates: dict[tuple[str, str], tuple[Decimal, int]] = {}

    for ps_el in _findall(product_el, "ProductSupply"):
        for sd_el in _findall(ps_el, "SupplyDetail"):
            for price_el in _findall(sd_el, "Price"):
                price_type = _text(price_el, "PriceType") or ""
                if price_type not in ("01", "02"):
                    continue
                # Skip inactive or not-yet-active prices
                price_status = _text(price_el, "PriceStatus")
                if price_status in ("04", "99"):
                    continue

                currency = _text(price_el, "CurrencyCode") or ""
                if currency not in ("GBP", "USD"):
                    continue

                amount_str = _text(price_el, "PriceAmount") or ""
                try:
                    amount = Decimal(amount_str)
                except InvalidOperation:
                    continue

                # Score territory specificity
                territory_el = _find(price_el, "Territory")
                if territory_el is None:
                    score = 0
                else:
                    countries_in = (_text(territory_el, "CountriesIncluded") or "").split()
                    regions_in = (_text(territory_el, "RegionsIncluded") or "").split()
                    if currency == "GBP" and "GB" in countries_in:
                        score = 2
                    elif currency == "USD" and "US" in countries_in:
                        score = 2
                    elif "WORLD" in regions_in:
                        score = 1
                    else:
                        score = 0

                key = (currency, price_type)
                existing = candidates.get(key)
                if existing is None or score > existing[1]:
                    candidates[key] = (amount, score)

    # Prefer inc-tax (02), fall back to exc-tax (01)
    for currency, col in (("GBP", "rrp_gbp"), ("USD", "rrp_usd")):
        best = candidates.get((currency, "02")) or candidates.get((currency, "01"))
        if best:
            out[col] = best[0]

    return out


# ─── Product assembler ────────────────────────────────────────────────────────

def _parse_product(product_el) -> ParsedBook | None:
    """
    Parse one <Product> element into a ParsedBook.
    Returns None if the record should be skipped (advance notice, missing ISBN/title).
    """
    record_ref = _text(product_el, "RecordReference") or ""
    notification_type = _text(product_el, "NotificationType") or "03"

    # 01/02 = early/advance notification — data may be incomplete, skip for now
    if notification_type in ("01", "02"):
        return None

    isbn13, isbn10 = _parse_identifiers(product_el)
    if not isbn13:
        return None  # no primary key

    descriptive = _parse_descriptive(product_el)
    title = descriptive.get("title") or ""
    if not title:
        return None  # incomplete record

    collateral = _parse_collateral(product_el)
    publishing = _parse_publishing(product_el)
    supply = _parse_supply(product_el)

    return ParsedBook(
        record_ref=record_ref,
        notification_type=notification_type,
        isbn13=isbn13,
        isbn10=isbn10,
        title=title,
        subtitle=descriptive.get("subtitle"),
        publisher_name=publishing.get("publisher_name"),
        imprint_name=publishing.get("imprint_name"),
        product_form=descriptive.get("product_form", "BA"),
        product_form_detail=descriptive.get("product_form_detail"),
        edition_number=descriptive.get("edition_number"),
        edition_statement=descriptive.get("edition_statement"),
        language_code=descriptive.get("language_code", "eng"),
        page_count=descriptive.get("page_count"),
        height_mm=descriptive.get("height_mm"),
        width_mm=descriptive.get("width_mm"),
        description=collateral.get("description"),
        toc=collateral.get("toc"),
        excerpt=collateral.get("excerpt"),
        audience_code=descriptive.get("audience_code"),
        publication_date=publishing.get("publication_date"),
        publishing_status=publishing.get("publishing_status"),
        out_of_print=publishing.get("out_of_print", False),
        uk_rights=publishing.get("uk_rights"),
        rrp_gbp=supply.get("rrp_gbp"),
        rrp_usd=supply.get("rrp_usd"),
        cover_image_url=collateral.get("cover_image_url"),
        contributors=descriptive.get("contributors", []),
        subjects=descriptive.get("subjects", []),
    )


# ─── Public API ───────────────────────────────────────────────────────────────

def parse_onix_file(
    source: str | Path | bytes | IO[bytes],
) -> Iterator[ParsedBook]:
    """
    Stream-parse an ONIX 3.0 (reference names) XML file.
    Yields one ParsedBook per valid <Product> element.

    Memory-bounded: each Product element is cleared after parsing.
    Handles both namespaced ONIX 3.0 (xmlns="http://ns.editeur.org/onix/3.0/reference")
    and files without a namespace declaration.

    Args:
        source: File path (str/Path), raw bytes, or binary file-like object.

    Yields:
        ParsedBook for each valid product (NotificationType 03 or 05).
        Skips: advance notices (01/02), products without ISBN-13, products without title.
    """
    if isinstance(source, bytes):
        source = BytesIO(source)

    context = etree.iterparse(source, events=("end",), recover=True)
    for _event, el in context:
        if _local(el) == "Product":
            try:
                parsed = _parse_product(el)
                if parsed is not None:
                    yield parsed
            finally:
                # Free memory: clear element content, then drop preceding siblings
                el.clear()
                while el.getprevious() is not None:
                    del el.getparent()[0]
