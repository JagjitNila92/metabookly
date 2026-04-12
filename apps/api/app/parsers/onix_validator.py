"""
ONIX feed validator — runs before ingest to catch structural and business-rule errors.

Returns a list of ValidationError objects, each with:
  - isbn13 (or None if the product has no ISBN yet)
  - field    — ONIX element path that failed
  - message  — human-readable explanation
  - line     — approximate line number in the XML (best-effort)
  - severity — "error" (blocks ingest) | "warning" (ingest continues)

The validator intentionally uses plain lxml without the full parser machinery so
it can give precise line numbers before the streaming parser loses position info.
"""
from __future__ import annotations

import re
from dataclasses import dataclass, field
from io import BytesIO

from lxml import etree


# ── ISBN-13 checksum ──────────────────────────────────────────────────────────

def _isbn13_valid(isbn: str) -> bool:
    """Return True if isbn is a valid 13-digit ISBN-13."""
    if not re.fullmatch(r"\d{13}", isbn):
        return False
    total = sum(int(d) * (1 if i % 2 == 0 else 3) for i, d in enumerate(isbn))
    return total % 10 == 0


# ── Valid ONIX codelist excerpts ──────────────────────────────────────────────

# ONIX List 1 — NotificationType
_VALID_NOTIFICATION_TYPES = {"01", "02", "03", "04", "05"}

# ONIX List 150 — ProductForm (common values)
_VALID_PRODUCT_FORMS = {
    "AA", "AB", "AC", "AD", "AE", "AF", "AG", "AH", "AI", "AJ", "AK", "AL", "AM",
    "BA", "BB", "BC", "BD", "BE", "BF", "BG", "BH", "BI", "BJ", "BK", "BL",
    "DA", "DB", "DC", "DD", "DE", "DF", "DG", "DH", "DI", "DZ",
    "EA", "EB", "EC", "ED", "FA", "FB", "FC", "MA", "MB", "MC", "VA", "VB", "VC",
    "WW", "XA", "XB", "XC", "XD", "XE", "XF", "XZ", "ZZ",
}

# ONIX publication date formats
_DATE_RE_YYYYMMDD = re.compile(r"^\d{8}$")
_DATE_RE_YYYYMM   = re.compile(r"^\d{6}$")
_DATE_RE_YYYY     = re.compile(r"^\d{4}$")


# ── Result types ──────────────────────────────────────────────────────────────

@dataclass
class ValidationError:
    isbn13:   str | None
    field:    str
    message:  str
    line:     int | None = None
    severity: str = "error"   # "error" | "warning"

    def to_dict(self) -> dict:
        return {
            "isbn13":    self.isbn13,
            "field":     self.field,
            "message":   self.message,
            "line":      self.line,
            "severity":  self.severity,
        }


@dataclass
class ValidationResult:
    passed:        bool
    error_count:   int
    warning_count: int
    errors:        list[ValidationError] = field(default_factory=list)

    # Cap stored errors to avoid huge payloads
    MAX_ERRORS = 100

    def add(self, err: ValidationError) -> None:
        if len(self.errors) < self.MAX_ERRORS:
            self.errors.append(err)
        if err.severity == "error":
            self.error_count += 1
        else:
            self.warning_count += 1

    def to_sample_list(self) -> list[dict]:
        return [e.to_dict() for e in self.errors]


# ── Namespace helpers ─────────────────────────────────────────────────────────

def _strip_ns(tag) -> str:
    """'{http://...}ProductIdentifier' → 'ProductIdentifier'"""
    tag = str(tag)  # lxml Cython builds can return a non-str callable for .tag
    return tag.split("}", 1)[1] if "}" in tag else tag


def _find_text(el: etree._Element, *paths: str) -> str | None:
    """Try a list of bare tag names (ns-agnostic) under el, return first text found."""
    for path in paths:
        for child in el:
            if _strip_ns(child.tag) == path:
                return (child.text or "").strip() or None
    return None


def _iter_children(el: etree._Element, tag: str):
    for child in el:
        if _strip_ns(child.tag) == tag:
            yield child


def _find_child(el: etree._Element, tag: str) -> etree._Element | None:
    for child in el:
        if _strip_ns(child.tag) == tag:
            return child
    return None


# ── Per-product validation ────────────────────────────────────────────────────

def _validate_product(product: etree._Element, result: ValidationResult) -> None:
    line = product.sourceline

    # ── 1. NotificationType ────────────────────────────────────────────────────
    notif_type = _find_text(product, "NotificationType")
    if not notif_type:
        result.add(ValidationError(
            isbn13=None, field="NotificationType", line=line,
            message="Missing <NotificationType>. Every product must declare its notification type.",
        ))
    elif notif_type not in _VALID_NOTIFICATION_TYPES:
        result.add(ValidationError(
            isbn13=None, field="NotificationType", line=line,
            message=f"Unknown NotificationType '{notif_type}'. Valid values: 01–05 (ONIX List 1).",
        ))

    # ── 2. ISBN-13 ─────────────────────────────────────────────────────────────
    isbn13: str | None = None
    for id_el in _iter_children(product, "ProductIdentifier"):
        id_type = _find_text(id_el, "ProductIDType")
        id_val  = _find_text(id_el, "IDValue")
        if id_type == "15":   # ISBN-13
            isbn13 = id_val
            break

    if not isbn13:
        result.add(ValidationError(
            isbn13=None, field="ProductIdentifier/IDValue[IDType=15]", line=line,
            message="Missing ISBN-13 (ProductIDType 15). Every product must have an ISBN-13.",
        ))
        return  # can't validate further without an ISBN

    if not _isbn13_valid(isbn13):
        result.add(ValidationError(
            isbn13=isbn13, field="ProductIdentifier/IDValue", line=line,
            message=f"Invalid ISBN-13 checksum: '{isbn13}'. Verify the digit sequence.",
        ))

    # ── 3. TitleDetail ─────────────────────────────────────────────────────────
    title_detail = _find_child(product, "DescriptiveDetail")
    if title_detail is not None:
        found_main_title = False
        for td in _iter_children(title_detail, "TitleDetail"):
            tt = _find_text(td, "TitleType")
            if tt == "01":
                te = _find_child(td, "TitleElement")
                if te is not None:
                    title_text = _find_text(te, "TitleText", "NoPrefix")
                    if title_text:
                        found_main_title = True
                        if len(title_text) < 2:
                            result.add(ValidationError(
                                isbn13=isbn13, field="TitleDetail/TitleElement/TitleText", line=line,
                                severity="warning",
                                message=f"Title is suspiciously short: '{title_text}'.",
                            ))
        if not found_main_title:
            result.add(ValidationError(
                isbn13=isbn13, field="DescriptiveDetail/TitleDetail[TitleType=01]", line=line,
                message="Missing main title (TitleType 01). A <TitleDetail> with TitleType 01 and a <TitleText> is required.",
            ))

        # ── 4. ProductForm ────────────────────────────────────────────────────
        product_form = _find_text(title_detail, "ProductForm")
        if not product_form:
            result.add(ValidationError(
                isbn13=isbn13, field="DescriptiveDetail/ProductForm", line=line,
                severity="warning",
                message="Missing <ProductForm>. Specify the format (e.g. BB=Paperback, BC=Hardback, DG=PDF ebook).",
            ))
        elif product_form not in _VALID_PRODUCT_FORMS:
            result.add(ValidationError(
                isbn13=isbn13, field="DescriptiveDetail/ProductForm", line=line,
                severity="warning",
                message=f"Unrecognised ProductForm code '{product_form}'. Check ONIX List 150.",
            ))
    else:
        # No DescriptiveDetail at all
        result.add(ValidationError(
            isbn13=isbn13, field="DescriptiveDetail", line=line,
            message="Missing <DescriptiveDetail> block. Title, format and contributors go here.",
        ))

    # ── 5. Publisher ───────────────────────────────────────────────────────────
    pub_detail = _find_child(product, "PublishingDetail")
    if pub_detail is None:
        result.add(ValidationError(
            isbn13=isbn13, field="PublishingDetail", line=line,
            severity="warning",
            message="Missing <PublishingDetail>. Publisher name and publication date should be here.",
        ))
    else:
        # Check publisher name
        has_publisher = False
        for pub_el in _iter_children(pub_detail, "Publisher"):
            role = _find_text(pub_el, "PublishingRole")
            name = _find_text(pub_el, "PublisherName")
            if role == "01" and name:
                has_publisher = True
                break
        if not has_publisher:
            result.add(ValidationError(
                isbn13=isbn13, field="PublishingDetail/Publisher[PublishingRole=01]/PublisherName", line=line,
                severity="warning",
                message="Missing publisher name (PublishingRole 01). Add a <Publisher> with role 01 and a <PublisherName>.",
            ))

        # ── 6. PublicationDate ────────────────────────────────────────────────
        pub_date_found = False
        for pd_el in _iter_children(pub_detail, "PublishingDate"):
            role = _find_text(pd_el, "PublishingDateRole")
            if role == "01":   # Publication date
                date_str = _find_text(pd_el, "Date")
                if date_str:
                    pub_date_found = True
                    if not (_DATE_RE_YYYYMMDD.match(date_str) or
                            _DATE_RE_YYYYMM.match(date_str) or
                            _DATE_RE_YYYY.match(date_str)):
                        result.add(ValidationError(
                            isbn13=isbn13, field="PublishingDetail/PublishingDate/Date", line=line,
                            message=(
                                f"Invalid date format '{date_str}'. "
                                "Use YYYYMMDD, YYYYMM, or YYYY (e.g. 20260315)."
                            ),
                        ))
        if not pub_date_found:
            result.add(ValidationError(
                isbn13=isbn13, field="PublishingDetail/PublishingDate[DateRole=01]", line=line,
                severity="warning",
                message="Missing publication date (PublishingDateRole 01). This is required for new titles.",
            ))

    # ── 7. Description (advisory) ─────────────────────────────────────────────
    if title_detail is not None:
        has_desc = False
        for ct_el in _iter_children(title_detail, "CollateralDetail"):
            for ta_el in _iter_children(ct_el, "TextContent"):
                tc_type = _find_text(ta_el, "TextType")
                if tc_type in ("02", "03"):  # short / long description
                    has_desc = True
                    text_val = _find_text(ta_el, "Text")
                    if text_val and len(text_val) < 50:
                        result.add(ValidationError(
                            isbn13=isbn13, field="CollateralDetail/TextContent/Text", line=line,
                            severity="warning",
                            message=f"Description is very short ({len(text_val)} chars). Aim for at least 150 characters for good discoverability.",
                        ))
        if not has_desc:
            result.add(ValidationError(
                isbn13=isbn13, field="CollateralDetail/TextContent[TextType=03]", line=line,
                severity="warning",
                message="No description found (TextType 02 or 03). Titles without descriptions are harder for booksellers to discover.",
            ))


# ── Entry point ───────────────────────────────────────────────────────────────

def validate_onix(content: bytes) -> ValidationResult:
    """
    Validate an ONIX 2.1 or 3.0 XML file.

    Returns a ValidationResult. Call result.passed to decide whether to proceed
    with ingest. Currently: ingest is always attempted but errors are surfaced
    to the publisher in the feed history UI.
    """
    result = ValidationResult(passed=True, error_count=0, warning_count=0)

    # ── Well-formed XML check ──────────────────────────────────────────────────
    try:
        root = etree.parse(BytesIO(content), parser=etree.XMLParser(
            recover=False,      # strict: don't silently fix bad XML
            resolve_entities=False,
            no_network=True,
        )).getroot()
    except etree.XMLSyntaxError as exc:
        result.add(ValidationError(
            isbn13=None, field="XML", line=getattr(exc, "lineno", None),
            message=f"XML syntax error: {exc.msg if hasattr(exc, 'msg') else str(exc)}. The file is not well-formed and cannot be processed.",
        ))
        result.passed = False
        return result

    # ── Detect ONIX version from root tag / namespace ──────────────────────────
    root_local = _strip_ns(str(root.tag))
    ns = root.nsmap.get(None, "") or ""
    is_onix3 = "3.0" in ns or root_local == "ONIXMessage"
    # ONIX 2.1 uses <ONIXMessage> with a 2.1 namespace; 3.0 uses same tag with 3.0 ns
    # Both use <Product> children, so validation logic is identical at this level.

    # ── Find all Product elements ──────────────────────────────────────────────
    products = [el for el in root if _strip_ns(el.tag) == "Product"]
    if not products:
        result.add(ValidationError(
            isbn13=None, field="ONIXMessage", line=1,
            message="No <Product> elements found. The feed appears to be empty.",
        ))
        result.passed = False
        return result

    # ── Validate each product ─────────────────────────────────────────────────
    for product in products:
        _validate_product(product, result)

    # A feed passes validation if it has no hard errors (warnings are fine)
    result.passed = result.error_count == 0
    return result
