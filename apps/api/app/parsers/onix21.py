"""ONIX 2.1 streaming XML parser.

Produces the same ParsedBook dataclass as the ONIX 3.0 parser, so the ingest
service can treat both versions identically.

Key structural differences from ONIX 3.0
─────────────────────────────────────────
  3.0 groups elements into composites: DescriptiveDetail, CollateralDetail,
  PublishingDetail, ProductSupply.
  2.1 puts everything directly under <Product> — no wrapper elements.

  Tag differences
  ───────────────
  Content text:  OtherText/TextTypeCode   vs 3.0 TextContent/TextType
  Cover image:   MediaFile                vs 3.0 SupportingResource
  Page count:    NumberOfPages            vs 3.0 Extent
  Dimensions:    MeasureTypeCode          vs 3.0 MeasureType
                 MeasureUnitCode (mm/cm/in) vs 3.0 MeasureUnit (03/01/02)
  Pricing:       PriceTypeCode            vs 3.0 PriceType
  Sales rights:  RightsTerritory / RightsCountry (space-sep codes)
                 vs 3.0 structured Territory composite
  Title:         Title/TitleText          vs 3.0 TitleDetail/TitleElement/TitleText
  Publisher:     Publisher direct child   vs 3.0 inside PublishingDetail
  Pub date:      PublicationDate          vs 3.0 PublishingDate/Date
  Pub status:    PublishingStatus         vs 3.0 inside PublishingDetail
"""
from __future__ import annotations

from io import BytesIO
from pathlib import Path
from typing import IO, Iterator

from lxml import etree

# Re-use shared dataclasses and pure helpers from the 3.0 parser
from app.parsers.onix3 import (
    ParsedBook,
    ParsedContributor,
    ParsedSubject,
    _local,
    _find,
    _findall,
    _text,
    _parse_date,
    _strip_html,
    _to_mm,
    _parse_identifiers,   # ProductIdentifier structure is identical in 2.1
)


# Regions that include Great Britain (same semantics as 3.0)
_REGIONS_INCL_GB = frozenset({"WORLD", "EUROPE", "EUROZ"})


def _territory_includes_gb_21(product_el) -> bool | None:
    """
    ONIX 2.1 uses flat RightsTerritory / RightsCountry text elements
    directly inside <SalesRights>, not a Territory composite.

    Returns:
      True  — for-sale right covers GB
      False — not-for-sale covers GB
      None  — no SalesRights present
    """
    for_sale = False
    not_for_sale = False
    found_any = False

    for sr_el in _findall(product_el, "SalesRights"):
        found_any = True
        sr_type = _text(sr_el, "SalesRightsType") or ""

        # RightsTerritory: space-separated region/country codes
        regions_raw = (_text(sr_el, "RightsTerritory") or "").split()
        countries_raw = (_text(sr_el, "RightsCountry") or "").split()
        all_codes = set(regions_raw) | set(countries_raw)

        covers_gb = (
            "GB" in all_codes
            or bool(all_codes & _REGIONS_INCL_GB)
        )

        if sr_type in ("01", "02", "06"):  # for sale
            if covers_gb:
                for_sale = True
        elif sr_type == "03":              # not for sale
            if covers_gb:
                not_for_sale = True

    if not found_any:
        return None
    if for_sale:
        return True
    if not_for_sale:
        return False
    return None


def _parse_product_21(product_el) -> ParsedBook | None:
    """Parse one ONIX 2.1 <Product> into a ParsedBook."""

    record_ref = _text(product_el, "RecordReference") or ""
    notification_type = _text(product_el, "NotificationType") or "03"

    if notification_type in ("01", "02"):
        return None

    isbn13, isbn10 = _parse_identifiers(product_el)
    if not isbn13:
        return None

    # ── Title ────────────────────────────────────────────────────────────────
    title = ""
    subtitle = None
    for title_el in _findall(product_el, "Title"):
        if _text(title_el, "TitleType") == "01":
            title = _text(title_el, "TitleText") or ""
            subtitle = _text(title_el, "Subtitle")
            break

    if not title:
        return None

    # ── Format ───────────────────────────────────────────────────────────────
    product_form = _text(product_el, "ProductForm") or "BA"
    product_form_detail = _text(product_el, "ProductFormDetail")

    # Edition
    edition_number = None
    en = _text(product_el, "EditionNumber")
    if en and en.isdigit():
        edition_number = int(en)
    edition_statement = _text(product_el, "EditionStatement")

    # Language (same composite structure as 3.0)
    language_code = "eng"
    for lang_el in _findall(product_el, "Language"):
        if _text(lang_el, "LanguageRole") == "01":
            code = _text(lang_el, "LanguageCode")
            if code:
                language_code = code
            break

    # Page count — ONIX 2.1 uses <NumberOfPages> directly
    page_count = None
    np_raw = _text(product_el, "NumberOfPages")
    if np_raw and np_raw.isdigit():
        page_count = int(np_raw)

    # ── Dimensions ───────────────────────────────────────────────────────────
    # MeasureTypeCode: "01"=height, "02"=width
    # MeasureUnitCode: "mm"=mm, "cm"=cm, "in"=inches (text codes, not numeric)
    height_mm = width_mm = None
    _unit_map_21 = {"mm": "03", "cm": "01", "in": "02"}
    for measure_el in _findall(product_el, "Measure"):
        m_type = _text(measure_el, "MeasureTypeCode")
        if m_type not in ("01", "02"):
            continue
        val_str = _text(measure_el, "Measurement") or ""
        unit_raw = (_text(measure_el, "MeasureUnitCode") or "mm").lower()
        unit = _unit_map_21.get(unit_raw, "03")
        try:
            mm = _to_mm(float(val_str), unit)
        except (ValueError, TypeError):
            continue
        if m_type == "01":
            height_mm = mm
        else:
            width_mm = mm

    # ── Audience ─────────────────────────────────────────────────────────────
    # 2.1: <AudienceCode> simple element OR <Audience> composite (same as 3.0)
    audience_code = _text(product_el, "AudienceCode")
    if not audience_code:
        for aud_el in _findall(product_el, "Audience"):
            if _text(aud_el, "AudienceCodeType") == "01":
                audience_code = _text(aud_el, "AudienceCodeValue")
                break

    # ── Content text (OtherText composites) ──────────────────────────────────
    # TextTypeCode: "01"=main description, "02"=short, "03"=long description,
    #               "04"=table of contents, "23"=excerpt/sample
    description = toc = excerpt = None
    for ot_el in _findall(product_el, "OtherText"):
        text_type = _text(ot_el, "TextTypeCode") or ""
        raw = _text(ot_el, "Text")
        if not raw:
            continue
        # TextFormat: "06"=XHTML, "02"=HTML, "01"=ASCII plain
        fmt = _text(ot_el, "TextFormat") or "01"
        clean = _strip_html(raw) if fmt in ("02", "06") else raw.strip()

        if text_type in ("03", "01") and description is None:
            description = clean
        elif text_type == "02" and description is None:
            description = clean
        elif text_type == "04" and toc is None:
            toc = clean
        elif text_type == "23" and excerpt is None:
            excerpt = clean

    # ── Cover image (MediaFile) ───────────────────────────────────────────────
    # MediaFileTypeCode: "04"=front cover image
    # MediaFileLinkTypeCode: "01"=URL
    cover_image_url = None
    for mf_el in _findall(product_el, "MediaFile"):
        if _text(mf_el, "MediaFileTypeCode") != "04":
            continue
        if _text(mf_el, "MediaFileLinkTypeCode") != "01":
            continue
        url = _text(mf_el, "MediaFileLink")
        if url:
            cover_image_url = url
            break  # take first; 2.1 rarely has multiple resolutions

    # ── Contributors (same composite structure as 3.0) ────────────────────────
    contributors: list[ParsedContributor] = []
    for contrib_el in _findall(product_el, "Contributor"):
        role = _text(contrib_el, "ContributorRole")
        if not role:
            continue
        person_name = _text(contrib_el, "PersonName")
        keys = _text(contrib_el, "KeyNames")
        before = _text(contrib_el, "NamesBeforeKey")
        if not person_name:
            if keys and before:
                person_name = f"{before} {keys}"
            elif keys:
                person_name = keys
            else:
                continue
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

    # ── Subjects ─────────────────────────────────────────────────────────────
    subjects: list[ParsedSubject] = []
    for subj_el in _findall(product_el, "Subject"):
        scheme = _text(subj_el, "SubjectSchemeIdentifier")
        code = _text(subj_el, "SubjectCode")
        if not scheme or not code:
            continue
        is_main = _find(subj_el, "MainSubject") is not None
        subjects.append(ParsedSubject(
            scheme_id=scheme,
            subject_code=code,
            subject_heading=_text(subj_el, "SubjectHeadingText"),
            main_subject=is_main,
        ))
    # BASICMainSubject → BIC code (SubjectSchemeIdentifier 12)
    bms = _text(product_el, "BASICMainSubject")
    if bms:
        subjects.insert(0, ParsedSubject(
            scheme_id="12",
            subject_code=bms,
            subject_heading=None,
            main_subject=True,
        ))

    # ── Publisher ─────────────────────────────────────────────────────────────
    publisher_name = imprint_name = None
    for pub_el in _findall(product_el, "Publisher"):
        if _text(pub_el, "PublishingRole") == "01":
            publisher_name = _text(pub_el, "PublisherName")
            break
    if not publisher_name:
        publisher_name = _text(product_el, "PublisherName")

    imprint_el = _find(product_el, "Imprint")
    if imprint_el is not None:
        imprint_name = _text(imprint_el, "ImprintName")

    # ── Publishing status + date ──────────────────────────────────────────────
    publishing_status = _text(product_el, "PublishingStatus")
    out_of_print = publishing_status in ("06", "07", "11", "12")

    pub_date_raw = _text(product_el, "PublicationDate")
    publication_date = _parse_date(pub_date_raw) if pub_date_raw else None

    # ── Sales rights → uk_rights ──────────────────────────────────────────────
    uk_rights = _territory_includes_gb_21(product_el)

    # ── RRP pricing ───────────────────────────────────────────────────────────
    # In 2.1: <SupplyDetail> directly under <Product>, uses <PriceTypeCode>
    rrp_gbp = rrp_usd = None
    from decimal import Decimal, InvalidOperation
    candidates: dict = {}
    for sd_el in _findall(product_el, "SupplyDetail"):
        for price_el in _findall(sd_el, "Price"):
            price_type = _text(price_el, "PriceTypeCode") or ""
            if price_type not in ("01", "02"):
                continue
            currency = _text(price_el, "CurrencyCode") or ""
            if currency not in ("GBP", "USD"):
                continue
            amount_str = _text(price_el, "PriceAmount") or ""
            try:
                amount = Decimal(amount_str)
            except InvalidOperation:
                continue
            key = (currency, price_type)
            if key not in candidates:
                candidates[key] = amount

    for currency, col_attr in (("GBP", "gbp"), ("USD", "usd")):
        best = candidates.get((currency, "02")) or candidates.get((currency, "01"))
        if best:
            if col_attr == "gbp":
                rrp_gbp = best
            else:
                rrp_usd = best

    return ParsedBook(
        record_ref=record_ref,
        notification_type=notification_type,
        isbn13=isbn13,
        isbn10=isbn10,
        title=title,
        subtitle=subtitle,
        publisher_name=publisher_name,
        imprint_name=imprint_name,
        product_form=product_form,
        product_form_detail=product_form_detail,
        edition_number=edition_number,
        edition_statement=edition_statement,
        language_code=language_code,
        page_count=page_count,
        height_mm=height_mm,
        width_mm=width_mm,
        description=description,
        toc=toc,
        excerpt=excerpt,
        audience_code=audience_code,
        publication_date=publication_date,
        publishing_status=publishing_status,
        out_of_print=out_of_print,
        uk_rights=uk_rights,
        rrp_gbp=rrp_gbp,
        rrp_usd=rrp_usd,
        cover_image_url=cover_image_url,
        contributors=contributors,
        subjects=subjects,
    )


def parse_onix21_file(
    source: str | Path | bytes | IO[bytes],
) -> Iterator[ParsedBook]:
    """
    Stream-parse an ONIX 2.1 XML file.
    Yields one ParsedBook per valid <Product> element.

    Handles both long-tag (reference) and numeric short-tag ONIX 2.1.
    Short tags (e.g. <a001> = RecordReference) are NOT supported — only
    reference (long) tag files. In practice, nearly all publisher-provided
    2.1 feeds use reference tags; short tags are a legacy EDI format.
    """
    if isinstance(source, bytes):
        source = BytesIO(source)

    context = etree.iterparse(source, events=("end",), recover=True)
    for _event, el in context:
        if _local(el) == "Product":
            try:
                parsed = _parse_product_21(el)
                if parsed is not None:
                    yield parsed
            finally:
                el.clear()
                while el.getprevious() is not None:
                    del el.getparent()[0]
