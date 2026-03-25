"""
ONIX parser dispatcher.

Detects the ONIX version from the file content and routes to the
appropriate parser. Both parsers yield the same ParsedBook dataclass.
"""
from __future__ import annotations

from io import BytesIO
from pathlib import Path
from typing import IO, Iterator

from app.parsers.onix3 import ParsedBook, parse_onix_file as _parse_30
from app.parsers.onix21 import parse_onix21_file as _parse_21


def detect_onix_version(peek: bytes) -> str:
    """
    Detect ONIX version from the first ~4 KB of the file.
    Returns "3.0" or "2.1".

    Detection heuristics (in priority order):
    1. ONIXMessage release="3.0" attribute → 3.0
    2. ONIX 3.0 namespace in xmlns declaration → 3.0
    3. Presence of 2.1-specific wrapper elements → 2.1
    4. Default → 3.0 (more common, 3.0 parser recovers gracefully)
    """
    sniff = peek[:4096].lower()
    if b'release="3.0"' in sniff or b"release='3.0'" in sniff:
        return "3.0"
    if b"ns.editeur.org/onix/3.0" in sniff:
        return "3.0"
    # 2.1 characteristic: no DescriptiveDetail in header (only shows up in body)
    # but 2.1 root element is typically <ONIXMessage> without release attr
    # If namespace contains "onix/2" it's definitely 2.1
    if b"ns.editeur.org/onix/2" in sniff:
        return "2.1"
    # Some 2.1 files declare release="2.1" explicitly
    if b'release="2.1"' in sniff or b"release='2.1'" in sniff:
        return "2.1"
    # Default to 3.0
    return "3.0"


def parse_onix_auto(
    source: str | Path | bytes | IO[bytes],
) -> tuple[str, Iterator[ParsedBook]]:
    """
    Auto-detect ONIX version and return (version_str, iterator).

    Usage:
        version, books = parse_onix_auto(content)
        for book in books:
            ...

    Returns:
        version: "2.1" or "3.0"
        iterator: yields ParsedBook objects
    """
    if isinstance(source, (str, Path)):
        raw = Path(source).read_bytes()
    elif isinstance(source, bytes):
        raw = source
    else:
        raw = source.read()

    version = detect_onix_version(raw)

    if version == "2.1":
        return version, _parse_21(raw)
    return version, _parse_30(raw)
