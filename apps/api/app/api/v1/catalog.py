import logging
from fastapi import APIRouter, BackgroundTasks, Depends, Query
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_db, get_optional_user
from app.auth.models import CurrentUser
from app.models.portal import SearchEvent
from app.models.retailer import Retailer
from app.schemas.catalog import FacetsResponse, SearchResponse
from app.services.catalog_service import get_facets, search_catalog

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/catalog", tags=["catalog"])


async def _log_search(
    db: AsyncSession,
    current_user: CurrentUser | None,
    query: str | None,
    filters: dict,
    result_count: int,
) -> None:
    try:
        retailer_id = None
        if current_user:
            retailer = (
                await db.execute(select(Retailer).where(Retailer.cognito_sub == current_user.sub))
            ).scalar_one_or_none()
            if retailer:
                retailer_id = retailer.id

        active_filters = {k: v for k, v in filters.items() if v is not None}
        db.add(SearchEvent(
            retailer_id=retailer_id,
            query=query,
            filters=active_filters or None,
            result_count=result_count,
            is_anonymous=retailer_id is None,
        ))
        await db.commit()
    except Exception as exc:
        logger.warning("Failed to log search event: %s", exc)


@router.get("/search", response_model=SearchResponse)
async def search(
    background_tasks: BackgroundTasks,
    q: str | None = Query(None),
    author: str | None = Query(None),
    publisher: str | None = Query(None),
    product_form: str | None = Query(None, description="ONIX product form code e.g. BB, BC"),
    subject_code: str | None = Query(None, description="BIC subject code"),
    language_code: str | None = Query(None, description="ISO 639-2 language code"),
    pub_date_from: str | None = Query(None, description="YYYY-MM-DD"),
    pub_date_to: str | None = Query(None, description="YYYY-MM-DD"),
    pub_date_preset: str | None = Query(None, description="new | recent | coming_soon | backlist"),
    in_print_only: bool = Query(True),
    uk_rights_only: bool = Query(False),
    price_band: str | None = Query(None, description="under10 | 10to20 | over20"),
    with_trade_price: bool = Query(False, description="Only show titles priced by the retailer's approved distributors"),
    sort: str | None = Query(None, description="newest | oldest | title_az | price_asc | price_desc | relevance | popular"),
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    db: AsyncSession = Depends(get_db),
    current_user: CurrentUser | None = Depends(get_optional_user),
) -> SearchResponse:
    # Resolve retailer_id for with_trade_price filter
    retailer_id = None
    if with_trade_price and current_user:
        retailer = (
            await db.execute(select(Retailer).where(Retailer.cognito_sub == current_user.sub))
        ).scalar_one_or_none()
        if retailer:
            retailer_id = retailer.id

    result = await search_catalog(
        db=db,
        q=q,
        author=author,
        publisher_name=publisher,
        product_form=product_form,
        subject_code=subject_code,
        language_code=language_code,
        pub_date_from=pub_date_from,
        pub_date_to=pub_date_to,
        pub_date_preset=pub_date_preset,
        in_print_only=in_print_only,
        uk_rights_only=uk_rights_only,
        price_band=price_band,
        with_trade_price=with_trade_price,
        retailer_id=retailer_id,
        sort=sort,
        page=page,
        page_size=page_size,
    )

    if q or author or publisher or product_form or subject_code:
        background_tasks.add_task(
            _log_search, db, current_user, q,
            {
                "author": author, "publisher": publisher,
                "product_form": product_form, "subject_code": subject_code,
                "language_code": language_code, "pub_date_preset": pub_date_preset,
                "uk_rights_only": uk_rights_only, "price_band": price_band,
                "with_trade_price": with_trade_price, "sort": sort,
            },
            result.total,
        )

    return result


@router.get("/facets", response_model=FacetsResponse)
async def catalog_facets(
    db: AsyncSession = Depends(get_db),
) -> FacetsResponse:
    """
    Subject category counts (BIC) and format counts for the active catalogue.
    Used to populate the filter sidebar. Cached for 5 minutes by the frontend.
    """
    return await get_facets(db)
