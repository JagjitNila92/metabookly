import math
import re
import uuid
from datetime import date, timedelta

from sqlalchemy import func, select, distinct, exists
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.models.book import Book, BookContributor, BookSubject, Publisher
from app.models.portal import BookDistributor, BookViewEvent, PriceCheckEvent
from app.models.retailer import RetailerDistributor
from app.schemas.catalog import FacetsResponse, FormatFacet, SearchResponse, SubjectFacet
from app.schemas.book import BookSummary, PublisherOut, ContributorOut

# ONIX product form code → human label
FORM_LABELS: dict[str, str] = {
    "BB": "Hardback",
    "BC": "Paperback",
    "BA": "Trade paperback",
    "BG": "Spiral bound",
    "AC": "Audio CD",
    "AJ": "Downloadable audio",
    "DG": "E-book",
    "DH": "E-book",
    "PI": "Illustrated",
    "ZZ": "Other",
}

# BIC subject scheme ID in book_subjects table
BIC_SCHEME = "12"

_ISBN_RE = re.compile(r"^97[89]\d{10}$|^\d{10}$")


def _is_isbn(q: str) -> bool:
    return bool(_ISBN_RE.match(q.replace("-", "").replace(" ", "")))


def _date_preset_range(preset: str) -> tuple[date | None, date | None]:
    """Return (from_date, to_date) for a named preset. None means open-ended."""
    today = date.today()
    if preset == "new":
        return today - timedelta(days=30), today
    if preset == "recent":
        return today - timedelta(days=90), today
    if preset == "coming_soon":
        return today + timedelta(days=1), None
    if preset == "backlist":
        return None, today - timedelta(days=365)
    return None, None


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
    pub_date_preset: str | None = None,
    in_print_only: bool = True,
    uk_rights_only: bool = False,
    price_band: str | None = None,       # "under10" | "10to20" | "over20"
    with_trade_price: bool = False,       # filter to titles the retailer can price
    retailer_id: uuid.UUID | None = None, # resolved from auth token when with_trade_price=True
    sort: str | None = None,              # "newest" | "oldest" | "title_az" | "price_asc" | "price_desc" | "relevance" | "popular"
    page: int = 1,
    page_size: int = 20,
) -> SearchResponse:
    page_size = min(page_size, 100)
    offset = (page - 1) * page_size

    # ISBN short-circuit: skip FTS and go straight to the book
    if q and _is_isbn(q):
        clean = q.replace("-", "").replace(" ", "")
        isbn13 = clean if len(clean) == 13 else None
        isbn10 = clean if len(clean) == 10 else None
        isbn_stmt = select(Book).options(
            selectinload(Book.publisher),
            selectinload(Book.contributors),
        )
        if isbn13:
            isbn_stmt = isbn_stmt.where(Book.isbn13 == isbn13)
        else:
            isbn_stmt = isbn_stmt.where(Book.isbn10 == isbn10)
        books = (await db.execute(isbn_stmt)).scalars().unique().all()
        return SearchResponse(
            results=[_to_summary(b) for b in books],
            total=len(books),
            page=1,
            page_size=page_size,
            pages=1 if books else 0,
            query=q,
        )

    stmt = select(Book).options(
        selectinload(Book.publisher),
        selectinload(Book.contributors),
    )

    # Full-text search
    has_query = q and q.strip()
    if has_query:
        stmt = stmt.where(
            Book.search_vector.op("@@")(
                func.websearch_to_tsquery("english", q)
            )
        )

    # Author filter
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

    # Format filter — exclude ebooks from default browse
    if product_form:
        stmt = stmt.where(Book.product_form == product_form)
    else:
        stmt = stmt.where(Book.product_form.notin_(["DG", "DH"]))

    # Subject filter
    if subject_code:
        stmt = stmt.join(BookSubject, BookSubject.book_id == Book.id).where(
            BookSubject.subject_code == subject_code,
            BookSubject.scheme_id == BIC_SCHEME,
        )

    # Language filter
    if language_code:
        stmt = stmt.where(Book.language_code == language_code)

    # Availability
    if in_print_only:
        stmt = stmt.where(Book.out_of_print == False)  # noqa: E712

    # UK rights
    if uk_rights_only:
        stmt = stmt.where(Book.uk_rights == True)  # noqa: E712

    # Price band
    if price_band == "under10":
        stmt = stmt.where(Book.rrp_gbp < 10)
    elif price_band == "10to20":
        stmt = stmt.where(Book.rrp_gbp >= 10, Book.rrp_gbp <= 20)
    elif price_band == "over20":
        stmt = stmt.where(Book.rrp_gbp > 20)

    # With trade price — filter to books carried by a distributor the retailer has
    # an approved account with. Joins book_distributors ↔ retailer_distributors.
    if with_trade_price and retailer_id is not None:
        stmt = stmt.where(
            exists(
                select(BookDistributor.id)
                .join(
                    RetailerDistributor,
                    RetailerDistributor.distributor_code == BookDistributor.distributor_code,
                )
                .where(
                    BookDistributor.book_id == Book.id,
                    RetailerDistributor.retailer_id == retailer_id,
                    RetailerDistributor.status == "approved",
                )
            )
        )

    # Date preset overrides manual date range
    if pub_date_preset:
        from_d, to_d = _date_preset_range(pub_date_preset)
        if from_d:
            stmt = stmt.where(Book.publication_date >= from_d)
        if to_d:
            stmt = stmt.where(Book.publication_date <= to_d)
    else:
        if pub_date_from:
            stmt = stmt.where(Book.publication_date >= pub_date_from)
        if pub_date_to:
            stmt = stmt.where(Book.publication_date <= pub_date_to)

    # Sort
    effective_sort = sort or ("relevance" if has_query else "newest")
    if effective_sort == "popular":
        # Demand-aware: rank by combined view + price-check event counts (last 90 days)
        cutoff = date.today() - timedelta(days=90)
        view_counts = (
            select(
                BookViewEvent.book_id,
                func.count(BookViewEvent.id).label("views"),
            )
            .where(BookViewEvent.created_at >= cutoff)
            .group_by(BookViewEvent.book_id)
            .subquery()
        )
        price_counts = (
            select(
                PriceCheckEvent.book_id,
                func.count(PriceCheckEvent.id).label("checks"),
            )
            .where(PriceCheckEvent.created_at >= cutoff)
            .group_by(PriceCheckEvent.book_id)
            .subquery()
        )
        stmt = (
            stmt
            .outerjoin(view_counts, view_counts.c.book_id == Book.id)
            .outerjoin(price_counts, price_counts.c.book_id == Book.id)
            .order_by(
                (
                    func.coalesce(view_counts.c.views, 0)
                    + func.coalesce(price_counts.c.checks, 0)
                ).desc(),
                Book.publication_date.desc().nullslast(),
            )
        )
    elif effective_sort == "relevance" and has_query:
        stmt = stmt.order_by(
            func.ts_rank(Book.search_vector, func.websearch_to_tsquery("english", q)).desc()
        )
    elif effective_sort == "oldest":
        stmt = stmt.order_by(Book.publication_date.asc().nullslast())
    elif effective_sort == "title_az":
        stmt = stmt.order_by(Book.title.asc())
    elif effective_sort == "price_asc":
        stmt = stmt.order_by(Book.rrp_gbp.asc().nullslast())
    elif effective_sort == "price_desc":
        stmt = stmt.order_by(Book.rrp_gbp.desc().nullslast())
    else:  # newest (default)
        stmt = stmt.order_by(Book.publication_date.desc().nullslast())

    # Count
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


async def get_facets(db: AsyncSession) -> FacetsResponse:
    """
    Return subject category counts (BIC scheme) and format counts
    for the active, in-print catalogue. Used to populate the filter sidebar.
    """
    # Top BIC subject categories by book count
    subject_rows = await db.execute(
        select(
            BookSubject.subject_code,
            BookSubject.subject_heading,
            func.count(distinct(BookSubject.book_id)).label("cnt"),
        )
        .join(Book, Book.id == BookSubject.book_id)
        .where(
            BookSubject.scheme_id == BIC_SCHEME,
            BookSubject.subject_heading.isnot(None),
            Book.out_of_print == False,  # noqa: E712
            Book.product_form.notin_(["DG", "DH"]),
        )
        .group_by(BookSubject.subject_code, BookSubject.subject_heading)
        .order_by(func.count(distinct(BookSubject.book_id)).desc())
        .limit(15)
    )

    subjects = [
        SubjectFacet(code=r.subject_code, label=r.subject_heading, count=r.cnt)
        for r in subject_rows.all()
    ]

    # Format counts
    format_rows = await db.execute(
        select(
            Book.product_form,
            func.count(Book.id).label("cnt"),
        )
        .where(Book.out_of_print == False)  # noqa: E712
        .group_by(Book.product_form)
        .order_by(func.count(Book.id).desc())
    )

    formats = [
        FormatFacet(
            code=r.product_form,
            label=FORM_LABELS.get(r.product_form, r.product_form),
            count=r.cnt,
        )
        for r in format_rows.all()
        if r.product_form not in ("DG", "DH")  # hide ebooks from format list
    ]

    return FacetsResponse(subjects=subjects, formats=formats)


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
