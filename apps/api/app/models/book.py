import uuid
from datetime import date, datetime
from decimal import Decimal
from sqlalchemy import Boolean, Date, ForeignKey, Index, Numeric, SmallInteger, Text, func
from sqlalchemy.dialects.postgresql import TSVECTOR, UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship
from app.db.base import Base


class Publisher(Base):
    __tablename__ = "publishers"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    name: Mapped[str] = mapped_column(Text, nullable=False, unique=True)
    imprint: Mapped[str | None] = mapped_column(Text)
    country_code: Mapped[str | None] = mapped_column(Text(2))
    created_at: Mapped[datetime] = mapped_column(default=func.now())
    updated_at: Mapped[datetime] = mapped_column(default=func.now(), onupdate=func.now())

    books: Mapped[list["Book"]] = relationship("Book", back_populates="publisher")


class Book(Base):
    __tablename__ = "books"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    isbn13: Mapped[str] = mapped_column(Text, nullable=False, unique=True)
    isbn10: Mapped[str | None] = mapped_column(Text)
    title: Mapped[str] = mapped_column(Text, nullable=False)
    subtitle: Mapped[str | None] = mapped_column(Text)
    publisher_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("publishers.id", ondelete="SET NULL")
    )
    imprint: Mapped[str | None] = mapped_column(Text)
    edition_number: Mapped[int | None] = mapped_column(SmallInteger)
    edition_statement: Mapped[str | None] = mapped_column(Text)
    language_code: Mapped[str] = mapped_column(Text, nullable=False, default="eng")
    product_form: Mapped[str] = mapped_column(Text, nullable=False)
    product_form_detail: Mapped[str | None] = mapped_column(Text)
    page_count: Mapped[int | None] = mapped_column(SmallInteger)
    description: Mapped[str | None] = mapped_column(Text)
    toc: Mapped[str | None] = mapped_column(Text)
    excerpt: Mapped[str | None] = mapped_column(Text)
    audience_code: Mapped[str | None] = mapped_column(Text)
    publication_date: Mapped[date | None] = mapped_column(Date)
    out_of_print: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    onix_record_ref: Mapped[str | None] = mapped_column(Text)
    cover_image_url: Mapped[str | None] = mapped_column(Text)

    # Fields added by migration 0002
    publishing_status: Mapped[str | None] = mapped_column(Text)        # ONIX list 64: "04"=active, "02"=forthcoming, "06"=OOP
    uk_rights: Mapped[bool | None] = mapped_column(Boolean)            # None = not stated
    rrp_gbp: Mapped[Decimal | None] = mapped_column(Numeric(10, 2))    # publisher list price GBP (reference only)
    rrp_usd: Mapped[Decimal | None] = mapped_column(Numeric(10, 2))    # publisher list price USD (reference only)

    # Fields added by migration 0004
    height_mm: Mapped[int | None] = mapped_column(SmallInteger)        # physical height in mm (ONIX MeasureType 01)
    width_mm: Mapped[int | None] = mapped_column(SmallInteger)         # physical width in mm (ONIX MeasureType 02)

    # Fields added by migration 0019 — computed on every ingest
    metadata_score: Mapped[int | None] = mapped_column(SmallInteger)   # 0–100 quality score

    created_at: Mapped[datetime] = mapped_column(default=func.now())
    updated_at: Mapped[datetime] = mapped_column(default=func.now(), onupdate=func.now())

    # Populated by DB trigger — never set from application code
    search_vector: Mapped[str | None] = mapped_column(TSVECTOR, nullable=True)

    # Relationships
    publisher: Mapped["Publisher | None"] = relationship("Publisher", back_populates="books")
    contributors: Mapped[list["BookContributor"]] = relationship(
        "BookContributor", back_populates="book", cascade="all, delete-orphan",
        order_by="BookContributor.sequence_number"
    )
    subjects: Mapped[list["BookSubject"]] = relationship(
        "BookSubject", back_populates="book", cascade="all, delete-orphan"
    )

    __table_args__ = (
        Index("books_search_vector_idx", "search_vector", postgresql_using="gin"),
        Index("books_publisher_id_idx", "publisher_id"),
        Index("books_product_form_idx", "product_form"),
        Index("books_publication_date_idx", "publication_date"),
        Index("books_out_of_print_idx", "out_of_print"),
    )


class BookContributor(Base):
    __tablename__ = "book_contributors"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    book_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("books.id", ondelete="CASCADE"), nullable=False
    )
    sequence_number: Mapped[int] = mapped_column(SmallInteger, nullable=False, default=1)
    role_code: Mapped[str] = mapped_column(Text, nullable=False)
    person_name: Mapped[str] = mapped_column(Text, nullable=False)
    person_name_inverted: Mapped[str | None] = mapped_column(Text)
    bio: Mapped[str | None] = mapped_column(Text)
    created_at: Mapped[datetime] = mapped_column(default=func.now())

    book: Mapped["Book"] = relationship("Book", back_populates="contributors")

    __table_args__ = (
        Index("book_contributors_book_id_idx", "book_id"),
    )


class BookSubject(Base):
    __tablename__ = "book_subjects"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    book_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("books.id", ondelete="CASCADE"), nullable=False
    )
    scheme_id: Mapped[str] = mapped_column(Text, nullable=False)
    subject_code: Mapped[str] = mapped_column(Text, nullable=False)
    subject_heading: Mapped[str | None] = mapped_column(Text)
    main_subject: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    created_at: Mapped[datetime] = mapped_column(default=func.now())

    book: Mapped["Book"] = relationship("Book", back_populates="subjects")

    __table_args__ = (
        Index("book_subjects_book_id_idx", "book_id"),
        Index("book_subjects_scheme_code_idx", "scheme_id", "subject_code"),
    )
