import math
from sqlalchemy import func, select, text
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.models.book import Book, BookContributor, Publisher
from app.schemas.catalog import SearchResponse
from app.schemas.book import BookSummary, PublisherOut, ContributorOut


async def search_catalog(
    db: AsyncSession,
    q: str | None = None,
    author: str | None = None,
    publisher_name: str | None = None,
    product_form: str | None = None,
    subject_code: str | None = None,
    language_code: str | None = None,
    pub_date_from: str | None = None,
    pub_date_to: str | None = None,
    in_print_only: bool = True,
    page: int = 1,
    page_size: int = 20,
) -> SearchResponse:
    page_size = min(page_size, 100)
    offset = (page - 1) * page_size

    # Base query with eager-loaded publisher and contributors
    stmt = (
        select(Book)
        .options(
            selectinload(Book.publisher),
            selectinload(Book.contributors),
        )
    )

    # Full-text search using websearch_to_tsquery (handles quoted phrases and - exclusions)
    if q and q.strip():
        stmt = stmt.where(
            Book.search_vector.op("@@")(
                func.websearch_to_tsquery("english", q)
            )
        ).order_by(
            func.ts_rank(Book.search_vector, func.websearch_to_tsquery("english", q)).desc()
        )
    else:
        stmt = stmt.order_by(Book.publication_date.desc())

    # Author filter — join to contributors, partial match
    if author:
        stmt = stmt.join(BookContributor, BookContributor.book_id == Book.id).where(
            BookContributor.role_code == "A01",
            func.lower(func.unaccent(BookContributor.person_name)).contains(
                func.lower(func.unaccent(author))
            ),
        )

    # Publisher filter
    if publisher_name:
        stmt = stmt.join(Publisher, Book.publisher_id == Publisher.id).where(
            func.lower(Publisher.name).contains(func.lower(publisher_name))
        )

    # Structured filters
    if product_form:
        stmt = stmt.where(Book.product_form == product_form)
    else:
        # Exclude digital formats (ebooks) from the default catalog view
        stmt = stmt.where(Book.product_form.notin_(["DG", "DH"]))
    if language_code:
        stmt = stmt.where(Book.language_code == language_code)
    if in_print_only:
        stmt = stmt.where(Book.out_of_print == False)  # noqa: E712
    if pub_date_from:
        stmt = stmt.where(Book.publication_date >= pub_date_from)
    if pub_date_to:
        stmt = stmt.where(Book.publication_date <= pub_date_to)
    if subject_code:
        from app.models.book import BookSubject
        stmt = stmt.join(BookSubject, BookSubject.book_id == Book.id).where(
            BookSubject.subject_code == subject_code
        )

    # Count total results
    count_stmt = select(func.count()).select_from(stmt.subquery())
    total = (await db.execute(count_stmt)).scalar_one()

    # Paginate
    stmt = stmt.offset(offset).limit(page_size)
    books = (await db.execute(stmt)).scalars().unique().all()

    return SearchResponse(
        results=[_to_summary(b) for b in books],
        total=total,
        page=page,
        page_size=page_size,
        pages=math.ceil(total / page_size) if total > 0 else 0,
        query=q,
    )


def _to_summary(book: Book) -> BookSummary:
    return BookSummary(
        id=book.id,
        isbn13=book.isbn13,
        title=book.title,
        subtitle=book.subtitle,
        product_form=book.product_form,
        language_code=book.language_code,
        publication_date=book.publication_date,
        cover_image_url=book.cover_image_url,
        out_of_print=book.out_of_print,
        publishing_status=book.publishing_status,
        uk_rights=book.uk_rights,
        rrp_gbp=str(book.rrp_gbp) if book.rrp_gbp is not None else None,
        rrp_usd=str(book.rrp_usd) if book.rrp_usd is not None else None,
        publisher=PublisherOut.model_validate(book.publisher) if book.publisher else None,
        contributors=[ContributorOut.model_validate(c) for c in book.contributors],
    )
