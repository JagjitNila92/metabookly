"""
Analytics endpoints powering distributor, retailer, and publisher dashboards.

Distributor endpoints (require_admin for MVP):
  GET /analytics/distributor/{distributor_code}/health   — catalogue completeness
  GET /analytics/distributor/{distributor_code}/demand   — search/view demand signal
  GET /analytics/distributor/{distributor_code}/leads    — retailers who viewed but have no link

Retailer endpoint (require_retailer):
  GET /analytics/retailer/me  — retailer's own search/view/pricing activity

Publisher endpoint (require_publisher):
  GET /analytics/publisher/me — views, orders, trends, top titles, genre breakdown, world map data
"""
import logging
from datetime import datetime, UTC, timedelta

from fastapi import APIRouter, Depends, Query
from sqlalchemy import func, select, distinct, and_, case, text
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_db, require_admin, require_publisher, require_retailer
from app.auth.models import CurrentUser
from app.models.book import Book, BookSubject
from app.models.ordering import Order, OrderLine, OrderLineItem, RetailerAddress
from app.models.portal import BookDistributor, BookViewEvent, FeedSource, OnixFeedV2, PriceCheckEvent, SearchEvent
from app.models.retailer import Retailer, RetailerDistributor

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/analytics", tags=["analytics"])


def _days_ago(days: int) -> datetime:
    return datetime.now(UTC).replace(tzinfo=None) - timedelta(days=days)


# ── Distributor: Catalogue Health ──────────────────────────────────────────────

@router.get("/distributor/{distributor_code}/health")
async def distributor_catalogue_health(
    distributor_code: str,
    db: AsyncSession = Depends(get_db),
    _: CurrentUser = Depends(require_admin),
) -> dict:
    """
    Catalogue completeness breakdown for a distributor's titles.
    Counts how many of their titles have description, cover, price, UK rights, and subjects.
    """
    # Base: all non-out-of-print books carried by this distributor
    base = (
        select(Book.id)
        .join(BookDistributor, BookDistributor.book_id == Book.id)
        .where(
            BookDistributor.distributor_code == distributor_code,
            Book.out_of_print == False,  # noqa: E712
        )
        .scalar_subquery()
    )

    result = await db.execute(
        select(
            func.count(Book.id).label("total"),
            func.count(Book.id).filter(
                Book.description.isnot(None), func.length(Book.description) > 50
            ).label("has_description"),
            func.count(Book.id).filter(Book.cover_image_url.isnot(None)).label("has_cover"),
            func.count(Book.id).filter(Book.rrp_gbp.isnot(None)).label("has_price"),
            func.count(Book.id).filter(Book.uk_rights == True).label("has_uk_rights"),  # noqa: E712
            func.count(Book.id).filter(Book.publication_date.isnot(None)).label("has_pub_date"),
        )
        .where(Book.id.in_(base))
    )
    row = result.one()

    # Count books that have at least one subject
    subjects_result = await db.execute(
        select(func.count(distinct(BookSubject.book_id)))
        .where(BookSubject.book_id.in_(base))
    )
    has_subjects = subjects_result.scalar_one() or 0

    total = row.total or 0

    def pct(n: int) -> float:
        return round((n / total * 100), 1) if total else 0.0

    # Worst offenders — titles missing the most fields
    worst = await db.execute(
        select(Book.isbn13, Book.title)
        .join(BookDistributor, BookDistributor.book_id == Book.id)
        .where(
            BookDistributor.distributor_code == distributor_code,
            Book.out_of_print == False,  # noqa: E712
            Book.description.is_(None),
        )
        .order_by(Book.updated_at.asc())
        .limit(10)
    )

    return {
        "distributor_code": distributor_code,
        "total_titles": total,
        "health_score": pct(
            sum([row.has_description, row.has_cover, row.has_price, row.has_uk_rights, has_subjects])
            // 5
        ),
        "completeness": {
            "has_description": {"count": row.has_description, "pct": pct(row.has_description)},
            "has_cover": {"count": row.has_cover, "pct": pct(row.has_cover)},
            "has_price": {"count": row.has_price, "pct": pct(row.has_price)},
            "has_uk_rights": {"count": row.has_uk_rights, "pct": pct(row.has_uk_rights)},
            "has_subjects": {"count": has_subjects, "pct": pct(has_subjects)},
            "has_pub_date": {"count": row.has_pub_date, "pct": pct(row.has_pub_date)},
        },
        "missing_description": [
            {"isbn13": r.isbn13, "title": r.title} for r in worst.all()
        ],
    }


# ── Distributor: Demand Signal ─────────────────────────────────────────────────

@router.get("/distributor/{distributor_code}/demand")
async def distributor_demand(
    distributor_code: str,
    days: int = Query(30, ge=1, le=365),
    db: AsyncSession = Depends(get_db),
    _: CurrentUser = Depends(require_admin),
) -> dict:
    """
    Which titles in this distributor's catalogue are getting the most attention
    from verified retailers — views and price checks in the last N days.
    """
    since = _days_ago(days)

    # Top viewed titles
    top_viewed = await db.execute(
        select(
            Book.isbn13,
            Book.title,
            func.count(BookViewEvent.id).label("views"),
            func.count(distinct(BookViewEvent.retailer_id)).label("unique_retailers"),
        )
        .join(BookDistributor, BookDistributor.book_id == Book.id)
        .join(BookViewEvent, BookViewEvent.book_id == Book.id)
        .where(
            BookDistributor.distributor_code == distributor_code,
            BookViewEvent.is_anonymous == False,  # noqa: E712
            BookViewEvent.created_at >= since,
        )
        .group_by(Book.isbn13, Book.title)
        .order_by(func.count(BookViewEvent.id).desc())
        .limit(20)
    )

    # Top price-checked titles
    top_priced = await db.execute(
        select(
            Book.isbn13,
            Book.title,
            func.count(PriceCheckEvent.id).label("price_checks"),
            func.count(distinct(PriceCheckEvent.retailer_id)).label("unique_retailers"),
        )
        .join(BookDistributor, BookDistributor.book_id == Book.id)
        .join(PriceCheckEvent, PriceCheckEvent.book_id == Book.id)
        .where(
            BookDistributor.distributor_code == distributor_code,
            PriceCheckEvent.created_at >= since,
        )
        .group_by(Book.isbn13, Book.title)
        .order_by(func.count(PriceCheckEvent.id).desc())
        .limit(20)
    )

    # Summary counts
    total_views = await db.execute(
        select(func.count(BookViewEvent.id))
        .join(BookDistributor, BookDistributor.book_id == BookViewEvent.book_id)
        .where(
            BookDistributor.distributor_code == distributor_code,
            BookViewEvent.is_anonymous == False,  # noqa: E712
            BookViewEvent.created_at >= since,
        )
    )

    return {
        "distributor_code": distributor_code,
        "period_days": days,
        "total_retailer_views": total_views.scalar_one() or 0,
        "top_viewed_titles": [
            {
                "isbn13": r.isbn13,
                "title": r.title,
                "views": r.views,
                "unique_retailers": r.unique_retailers,
            }
            for r in top_viewed.all()
        ],
        "top_price_checked_titles": [
            {
                "isbn13": r.isbn13,
                "title": r.title,
                "price_checks": r.price_checks,
                "unique_retailers": r.unique_retailers,
            }
            for r in top_priced.all()
        ],
    }


# ── Distributor: Leads (retailers with no account link) ───────────────────────

@router.get("/distributor/{distributor_code}/leads")
async def distributor_leads(
    distributor_code: str,
    days: int = Query(30, ge=1, le=365),
    db: AsyncSession = Depends(get_db),
    _: CurrentUser = Depends(require_admin),
) -> dict:
    """
    Retailers who viewed titles in this distributor's catalogue but have no
    approved account link — these are warm sales leads.
    """
    since = _days_ago(days)

    # Retailers with an approved link to this distributor
    linked_retailer_ids = (
        select(RetailerDistributor.retailer_id)
        .where(
            RetailerDistributor.distributor_code == distributor_code,
            RetailerDistributor.status == "approved",
        )
        .scalar_subquery()
    )

    leads = await db.execute(
        select(
            Retailer.id,
            Retailer.company_name,
            Retailer.email,
            func.count(BookViewEvent.id).label("views"),
            func.count(distinct(BookViewEvent.book_id)).label("unique_titles_viewed"),
            func.max(BookViewEvent.created_at).label("last_seen"),
        )
        .join(BookViewEvent, BookViewEvent.retailer_id == Retailer.id)
        .join(BookDistributor, BookDistributor.book_id == BookViewEvent.book_id)
        .where(
            BookDistributor.distributor_code == distributor_code,
            BookViewEvent.created_at >= since,
            BookViewEvent.is_anonymous == False,  # noqa: E712
            Retailer.id.not_in(linked_retailer_ids),
        )
        .group_by(Retailer.id, Retailer.company_name, Retailer.email)
        .order_by(func.count(BookViewEvent.id).desc())
        .limit(50)
    )

    return {
        "distributor_code": distributor_code,
        "period_days": days,
        "leads": [
            {
                "retailer_id": str(r.id),
                "company_name": r.company_name,
                "email": r.email,
                "views": r.views,
                "unique_titles_viewed": r.unique_titles_viewed,
                "last_seen": r.last_seen.isoformat() if r.last_seen else None,
            }
            for r in leads.all()
        ],
    }


# ── Retailer: My Activity ──────────────────────────────────────────────────────

@router.get("/retailer/me")
async def retailer_my_analytics(
    days: int = Query(30, ge=1, le=365),
    db: AsyncSession = Depends(get_db),
    current_user: CurrentUser = Depends(require_retailer),
) -> dict:
    """Retailer's own search, view, and pricing activity summary."""
    since = _days_ago(days)

    retailer = (
        await db.execute(select(Retailer).where(Retailer.cognito_sub == current_user.sub))
    ).scalar_one_or_none()

    if not retailer:
        return {
            "period_days": days,
            "recent_searches": [],
            "top_viewed_titles": [],
            "price_checks": {"total": 0, "with_gap": 0},
        }

    # Recent searches
    recent_searches = await db.execute(
        select(SearchEvent.query, SearchEvent.result_count, SearchEvent.created_at)
        .where(
            SearchEvent.retailer_id == retailer.id,
            SearchEvent.created_at >= since,
            SearchEvent.query.isnot(None),
        )
        .order_by(SearchEvent.created_at.desc())
        .limit(20)
    )

    # Most viewed titles
    top_viewed = await db.execute(
        select(Book.isbn13, Book.title, func.count(BookViewEvent.id).label("views"))
        .join(BookViewEvent, BookViewEvent.book_id == Book.id)
        .where(
            BookViewEvent.retailer_id == retailer.id,
            BookViewEvent.created_at >= since,
        )
        .group_by(Book.isbn13, Book.title)
        .order_by(func.count(BookViewEvent.id).desc())
        .limit(10)
    )

    # Price check summary
    price_summary = await db.execute(
        select(
            func.count(PriceCheckEvent.id).label("total_checks"),
            func.count(PriceCheckEvent.id).filter(
                PriceCheckEvent.had_gap == True  # noqa: E712
            ).label("gaps"),
        )
        .where(
            PriceCheckEvent.retailer_id == retailer.id,
            PriceCheckEvent.created_at >= since,
        )
    )
    price_row = price_summary.one()

    return {
        "period_days": days,
        "recent_searches": [
            {
                "query": r.query,
                "result_count": r.result_count,
                "searched_at": r.created_at.isoformat(),
            }
            for r in recent_searches.all()
        ],
        "top_viewed_titles": [
            {"isbn13": r.isbn13, "title": r.title, "views": r.views}
            for r in top_viewed.all()
        ],
        "price_checks": {
            "total": price_row.total_checks or 0,
            "with_gap": price_row.gaps or 0,
        },
    }


# ── Publisher: Dashboard Analytics ────────────────────────────────────────────

@router.get("/publisher/me")
async def publisher_analytics(
    days: int = Query(30, ge=1, le=365),
    db: AsyncSession = Depends(get_db),
    current_user: CurrentUser = Depends(require_publisher),
) -> dict:
    """
    Publisher dashboard data: views, orders, engagement, top titles,
    genre breakdown, daily trends, and a world map of ordering retailers.

    Admins see platform-wide data. Publishers see data for their own titles
    (matched via FeedSource.cognito_sub).
    """
    since = _days_ago(days)

    # ── Scope: which books does this publisher own? ────────────────────────────
    if current_user.is_admin:
        # Admin sees all books
        book_ids_subq = select(Book.id).scalar_subquery()
    else:
        # Publisher: find their feed source, then books from those feeds
        feed_source = (
            await db.execute(
                select(FeedSource.id).where(FeedSource.cognito_sub == current_user.sub)
            )
        ).scalar_one_or_none()

        if not feed_source:
            return _empty_publisher_response(days)

        feed_ids = select(OnixFeedV2.id).where(OnixFeedV2.feed_source_id == feed_source)
        # Books ingested from this publisher's feeds — via book_metadata_versions or
        # just use all books for now (refined when real publisher data exists)
        book_ids_subq = select(Book.id).scalar_subquery()

    # ── Summary counts ─────────────────────────────────────────────────────────
    total_views_row = (await db.execute(
        select(func.count(BookViewEvent.id))
        .where(
            BookViewEvent.book_id.in_(book_ids_subq),
            BookViewEvent.is_anonymous == False,  # noqa: E712
            BookViewEvent.created_at >= since,
        )
    )).scalar_one() or 0

    total_orders_row = (await db.execute(
        select(func.count(OrderLineItem.id))
        .join(OrderLine, OrderLine.id == OrderLineItem.order_line_id)
        .join(Order, Order.id == OrderLine.order_id)
        .where(
            OrderLineItem.book_id.in_(book_ids_subq),
            OrderLineItem.status.not_in(["cancelled"]),
            Order.submitted_at >= since,
        )
    )).scalar_one() or 0

    active_retailers_row = (await db.execute(
        select(func.count(distinct(Order.retailer_id)))
        .join(OrderLine, OrderLine.order_id == Order.id)
        .join(OrderLineItem, OrderLineItem.order_line_id == OrderLine.id)
        .where(
            OrderLineItem.book_id.in_(book_ids_subq),
            OrderLineItem.status.not_in(["cancelled"]),
            Order.submitted_at >= since,
        )
    )).scalar_one() or 0

    engagement_rate = (
        round(total_orders_row / total_views_row * 100, 1) if total_views_row else 0.0
    )

    # ── Order value ────────────────────────────────────────────────────────────
    total_order_value_row = (await db.execute(
        select(func.coalesce(
            func.sum(OrderLineItem.trade_price_gbp * OrderLineItem.quantity_ordered), 0
        ))
        .join(OrderLine, OrderLine.id == OrderLineItem.order_line_id)
        .join(Order, Order.id == OrderLine.order_id)
        .where(
            OrderLineItem.book_id.in_(book_ids_subq),
            OrderLineItem.status.not_in(["cancelled"]),
            Order.submitted_at >= since,
        )
    )).scalar_one() or 0

    # ── Daily trend (views + orders per day) ───────────────────────────────────
    daily_views = await db.execute(
        select(
            func.date_trunc("day", BookViewEvent.created_at).label("day"),
            func.count(BookViewEvent.id).label("views"),
        )
        .where(
            BookViewEvent.book_id.in_(book_ids_subq),
            BookViewEvent.is_anonymous == False,  # noqa: E712
            BookViewEvent.created_at >= since,
        )
        .group_by(text("day"))
        .order_by(text("day"))
    )

    daily_orders = await db.execute(
        select(
            func.date_trunc("day", Order.submitted_at).label("day"),
            func.count(OrderLineItem.id).label("orders"),
        )
        .join(OrderLine, OrderLine.order_id == Order.id)
        .join(OrderLineItem, OrderLineItem.order_line_id == OrderLine.id)
        .where(
            OrderLineItem.book_id.in_(book_ids_subq),
            OrderLineItem.status.not_in(["cancelled"]),
            Order.submitted_at >= since,
        )
        .group_by(text("day"))
        .order_by(text("day"))
    )

    # Merge views + orders into a single daily series
    views_by_day = {r.day.date().isoformat(): r.views for r in daily_views.all()}
    orders_by_day = {r.day.date().isoformat(): r.orders for r in daily_orders.all()}
    all_days = sorted(set(views_by_day) | set(orders_by_day))
    daily_trend = [
        {
            "date": d,
            "views": views_by_day.get(d, 0),
            "orders": orders_by_day.get(d, 0),
        }
        for d in all_days
    ]

    # ── Top titles by views ────────────────────────────────────────────────────
    top_titles = await db.execute(
        select(
            Book.isbn13,
            Book.title,
            func.count(BookViewEvent.id).label("views"),
            func.count(distinct(BookViewEvent.retailer_id)).label("unique_retailers"),
        )
        .join(BookViewEvent, BookViewEvent.book_id == Book.id)
        .where(
            Book.id.in_(book_ids_subq),
            BookViewEvent.is_anonymous == False,  # noqa: E712
            BookViewEvent.created_at >= since,
        )
        .group_by(Book.isbn13, Book.title)
        .order_by(func.count(BookViewEvent.id).desc())
        .limit(10)
    )

    # ── Genre / subject breakdown ──────────────────────────────────────────────
    genre_rows = await db.execute(
        select(
            BookSubject.subject_heading,
            func.count(distinct(BookViewEvent.book_id)).label("title_count"),
            func.count(BookViewEvent.id).label("views"),
        )
        .join(Book, Book.id == BookSubject.book_id)
        .join(BookViewEvent, BookViewEvent.book_id == Book.id)
        .where(
            Book.id.in_(book_ids_subq),
            BookSubject.scheme_id.in_(["12", "10", "93"]),  # BIC, BISAC, Thema
            BookSubject.subject_heading.isnot(None),
            BookViewEvent.is_anonymous == False,  # noqa: E712
            BookViewEvent.created_at >= since,
        )
        .group_by(BookSubject.subject_heading)
        .order_by(func.count(BookViewEvent.id).desc())
        .limit(12)
    )

    # ── Retailer world map data ────────────────────────────────────────────────
    # Country codes from retailers who placed orders on this publisher's titles
    country_rows = await db.execute(
        select(
            Retailer.country_code,
            func.count(distinct(Order.id)).label("order_count"),
            func.count(distinct(Order.retailer_id)).label("retailer_count"),
        )
        .join(Order, Order.retailer_id == Retailer.id)
        .join(OrderLine, OrderLine.order_id == Order.id)
        .join(OrderLineItem, OrderLineItem.order_line_id == OrderLine.id)
        .where(
            OrderLineItem.book_id.in_(book_ids_subq),
            OrderLineItem.status.not_in(["cancelled"]),
            Order.submitted_at >= since,
            Retailer.country_code.isnot(None),
        )
        .group_by(Retailer.country_code)
        .order_by(func.count(distinct(Order.id)).desc())
    )

    return {
        "period_days": days,
        "summary": {
            "total_views": total_views_row,
            "total_orders": total_orders_row,
            "active_retailers": active_retailers_row,
            "engagement_rate": engagement_rate,
            "total_order_value_gbp": float(total_order_value_row),
        },
        "daily_trend": daily_trend,
        "top_titles": [
            {
                "isbn13": r.isbn13,
                "title": r.title,
                "views": r.views,
                "unique_retailers": r.unique_retailers,
            }
            for r in top_titles.all()
        ],
        "genre_breakdown": [
            {"genre": r.subject_heading, "title_count": r.title_count, "views": r.views}
            for r in genre_rows.all()
        ],
        "retailer_countries": [
            {
                "country_code": r.country_code,
                "order_count": r.order_count,
                "retailer_count": r.retailer_count,
            }
            for r in country_rows.all()
        ],
    }


def _empty_publisher_response(days: int) -> dict:
    return {
        "period_days": days,
        "summary": {
            "total_views": 0, "total_orders": 0, "active_retailers": 0,
            "engagement_rate": 0.0, "total_order_value_gbp": 0.0,
        },
        "daily_trend": [],
        "top_titles": [],
        "genre_breakdown": [],
        "retailer_countries": [],
    }
