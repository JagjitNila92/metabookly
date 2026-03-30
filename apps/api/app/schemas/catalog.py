from pydantic import BaseModel, Field
from app.schemas.book import BookSummary


class SearchResponse(BaseModel):
    results: list[BookSummary]
    total: int
    page: int
    page_size: int
    pages: int
    query: str | None = None


class SubjectFacet(BaseModel):
    code: str
    label: str
    count: int


class FormatFacet(BaseModel):
    code: str
    label: str
    count: int


class FacetsResponse(BaseModel):
    subjects: list[SubjectFacet]
    formats: list[FormatFacet]


# ─── Bulk ISBN lookup ──────────────────────────────────────────────────────────

class BulkLookupRequest(BaseModel):
    isbns: list[str] = Field(..., min_length=1, max_length=500)


class OutOfPrintEntry(BaseModel):
    isbn13: str
    title: str | None
    publisher_name: str | None


class BulkLookupResponse(BaseModel):
    matched: list[BookSummary]          # in-print, in catalog
    out_of_print: list[OutOfPrintEntry] # in catalog but OOP
    not_found: list[str]                # raw ISBNs not in catalog
    duplicates_removed: int             # count of dupes merged in input
