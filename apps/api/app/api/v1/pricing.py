import asyncio
import logging
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_current_user
from app.auth.models import CurrentUser
from app.aws.secrets import get_retailer_distributor_credentials
from app.connectors.registry import get_connector
from app.db.session import get_db
from app.models.book import Book
from app.models.retailer import Retailer, RetailerDistributor
from app.schemas.pricing import (
    AvailabilityResponse,
    BatchAvailabilityRequest,
    BatchAvailabilityResponse,
    DistributorPrice,
)

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/books", tags=["pricing"])


async def _fetch_price_for_distributor(
    isbn13: str,
    retailer_id: str,
    account: RetailerDistributor,
) -> DistributorPrice:
    """Fetch price from one distributor — returns error DistributorPrice on failure."""
    try:
        credentials = get_retailer_distributor_credentials(
            retailer_id=str(retailer_id),
            distributor_code=account.distributor_code,
        )
        connector = get_connector(account.distributor_code)
        return await connector.get_price_availability(isbn13, credentials)
    except Exception as e:
        logger.warning("Distributor %s failed for ISBN %s: %s",
                       account.distributor_code, isbn13, e)
        return DistributorPrice(
            distributor_code=account.distributor_code,
            distributor_name=account.distributor_code,
            available=False,
            error=str(e),
        )


@router.get("/{isbn13}/availability", response_model=AvailabilityResponse)
async def get_availability(
    isbn13: str,
    db: AsyncSession = Depends(get_db),
    current_user: CurrentUser = Depends(get_current_user),
) -> AvailabilityResponse:
    # Verify book exists
    book = (await db.execute(select(Book).where(Book.isbn13 == isbn13))).scalar_one_or_none()
    if not book:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Book not found")

    # Get retailer record
    retailer = (
        await db.execute(select(Retailer).where(Retailer.cognito_sub == current_user.sub))
    ).scalar_one_or_none()
    if not retailer:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Retailer not found")

    # Get all active distributor accounts for this retailer
    accounts = (
        await db.execute(
            select(RetailerDistributor)
            .where(RetailerDistributor.retailer_id == retailer.id)
            .where(RetailerDistributor.active == True)  # noqa: E712
        )
    ).scalars().all()

    if not accounts:
        return AvailabilityResponse(isbn13=isbn13, distributors=[])

    # Fan out to all distributors concurrently — partial failures are returned, not raised
    results = await asyncio.gather(
        *[_fetch_price_for_distributor(isbn13, str(retailer.id), account)
          for account in accounts],
        return_exceptions=False,
    )

    return AvailabilityResponse(isbn13=isbn13, distributors=list(results))


@router.post("/availability/batch", response_model=BatchAvailabilityResponse)
async def get_batch_availability(
    request: BatchAvailabilityRequest,
    db: AsyncSession = Depends(get_db),
    current_user: CurrentUser = Depends(get_current_user),
) -> BatchAvailabilityResponse:
    if len(request.isbns) > 50:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Maximum 50 ISBNs per batch request",
        )

    retailer = (
        await db.execute(select(Retailer).where(Retailer.cognito_sub == current_user.sub))
    ).scalar_one_or_none()
    if not retailer:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Retailer not found")

    accounts = (
        await db.execute(
            select(RetailerDistributor)
            .where(RetailerDistributor.retailer_id == retailer.id)
            .where(RetailerDistributor.active == True)  # noqa: E712
        )
    ).scalars().all()

    results: dict[str, list[DistributorPrice]] = {}
    for isbn13 in request.isbns:
        prices = await asyncio.gather(
            *[_fetch_price_for_distributor(isbn13, str(retailer.id), account)
              for account in accounts],
            return_exceptions=False,
        )
        results[isbn13] = list(prices)

    return BatchAvailabilityResponse(results=results)
