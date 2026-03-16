from pydantic import BaseModel, Field
from app.schemas.book import BookSummary


class SearchResponse(BaseModel):
    results: list[BookSummary]
    total: int
    page: int
    page_size: int
    pages: int
    query: str | None = None
