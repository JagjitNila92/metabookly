from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_current_user
from app.auth.models import CurrentUser
from app.db.session import get_db
from app.schemas.catalog import SearchResponse
from app.services.catalog_service import search_catalog

router = APIRouter(prefix="/catalog", tags=["catalog"])


@router.get("/search", response_model=SearchResponse)
async def search(
    q: str | None = Query(None, description="Free-text search (title, author, description)"),
    author: str | None = Query(None, description="Filter by author name (partial match)"),
    publisher: str | None = Query(None, description="Filter by publisher name (partial match)"),
    product_form: str | None = Query(None, description="ONIX product form code (e.g. BB, BC, DG)"),
    subject_code: str | None = Query(None, description="BIC or THEMA subject code"),
    language_code: str | None = Query(None, description="ISO 639-2 language code (e.g. eng, fre)"),
    pub_date_from: str | None = Query(None, description="Publication date from (YYYY-MM-DD)"),
    pub_date_to: str | None = Query(None, description="Publication date to (YYYY-MM-DD)"),
    in_print_only: bool = Query(True, description="Exclude out-of-print titles"),
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    db: AsyncSession = Depends(get_db),
    _: CurrentUser = Depends(get_current_user),
) -> SearchResponse:
    return await search_catalog(
        db=db,
        q=q,
        author=author,
        publisher_name=publisher,
        product_form=product_form,
        subject_code=subject_code,
        language_code=language_code,
        pub_date_from=pub_date_from,
        pub_date_to=pub_date_to,
        in_print_only=in_print_only,
        page=page,
        page_size=page_size,
    )
