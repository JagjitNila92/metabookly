from pydantic import BaseModel
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
