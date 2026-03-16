import uuid
from datetime import date, datetime
from pydantic import BaseModel, ConfigDict


class ContributorOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: uuid.UUID
    role_code: str
    person_name: str
    person_name_inverted: str | None = None
    bio: str | None = None
    sequence_number: int


class SubjectOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    scheme_id: str
    subject_code: str
    subject_heading: str | None = None
    main_subject: bool


class PublisherOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: uuid.UUID
    name: str
    imprint: str | None = None


class BookSummary(BaseModel):
    """Lightweight schema for catalog search results."""
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    isbn13: str
    title: str
    subtitle: str | None = None
    product_form: str
    language_code: str
    publication_date: date | None = None
    cover_image_url: str | None = None
    out_of_print: bool
    publisher: PublisherOut | None = None
    contributors: list[ContributorOut] = []


class BookDetail(BookSummary):
    """Full schema for book detail page."""
    isbn10: str | None = None
    edition_number: int | None = None
    edition_statement: str | None = None
    page_count: int | None = None
    description: str | None = None
    toc: str | None = None
    excerpt: str | None = None
    audience_code: str | None = None
    product_form_detail: str | None = None
    subjects: list[SubjectOut] = []
    created_at: datetime
    updated_at: datetime
