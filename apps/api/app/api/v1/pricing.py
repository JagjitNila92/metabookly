import asyncio
import logging
import uuid
from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_current_user, get_db
from app.auth.models import CurrentUser
from app.aws.secrets import get_retailer_distributor_credentials
from app.connectors.registry import get_connector
from app.models.book import Book
from app.models.portal import PriceCheckEvent
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
        connector = get_connector(account.distributor_code)
        credentials = (
            get_retailer_distributor_credentials(
                retailer_id=str(retailer_id),
                distributor_code=account.distributor_code,
            )
            if connector.requires_credentials
            else {}
        )
        return await connector.get_price_availability(isbn13, credentials)
    except Exception as e:
        logger.warning("Distributor %s failed for ISBN %s: %s",
                       account.distributor_code, isbn13, e)
        msg = str(e)
        if any(k in msg for k in ("SecretValue", "SecretString", "Secrets Manager", "credentials")):
            msg = "Distributor credentials not yet configured for this environment"
        elif isinstance(e, NotImplementedError):
            msg = "Distributor integration not yet available"
        return DistributorPrice(
            distributor_code=account.distributor_code,
            distributor_name=account.distributor_code,
            available=False,
            error=msg,
        )


async def _log_price_check(
    db: AsyncSession,
    retailer_id: uuid.UUID,
    book_id: uuid.UUID,
    isbn13: str,
    accounts: list[RetailerDistributor],
    results: list[DistributorPrice],
) -> None:
    """Fire-and-forget: record what was queried and what returned a price."""
    try:
        queried = [a.distributor_code for a in accounts]
        with_price = [r.distributor_code for r in results if r.available and not r.error]
        had_gap = len(queried) > 0 and len(with_price) == 0
        db.add(PriceCheckEvent(
            retailer_id=retailer_id,
            book_id=book_id,
            isbn13=isbn13,
            distributors_queried=queried,
            distributors_with_price=with_price,
            had_gap=had_gap,
        ))
        await db.commit()
    except Exception as exc:
        logger.warning("Failed to log price check event: %s", exc)


@router.get("/{isbn13}/availability", response_model=AvailabilityResponse)
async def get_availability(
    isbn13: str,
    background_tasks: BackgroundTasks,
    db: AsyncSession = Depends(get_db),
    current_user: CurrentUser = Depends(get_current_user),
) -> AvailabilityResponse:
    book = (await db.execute(select(Book).where(Book.isbn13 == isbn13))).scalar_one_or_none()
    if not book:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Book not found")

    retailer = (
        await db.execute(select(Retailer).where(Retailer.cognito_sub == current_user.sub))
    ).scalar_one_or_none()
    if not retailer:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Retailer not found")

    # Only approved accounts can be used for pricing
    accounts = (
        await db.execute(
            select(RetailerDistributor)
            .where(
                RetailerDistributor.retailer_id == retailer.id,
                RetailerDistributor.status == "approved",
            )
        )
    ).scalars().all()

    if not accounts:
        return AvailabilityResponse(isbn13=isbn13, distributors=[])

    results = await asyncio.gather(
        *[_fetch_price_for_distributor(isbn13, str(retailer.id), account)
          for account in accounts],
        return_exceptions=False,
    )
    results = list(results)

    background_tasks.add_task(
        _log_price_check, db, retailer.id, book.id, isbn13, accounts, results
    )

    return AvailabilityResponse(isbn13=isbn13, distributors=results)


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
            .where(
                RetailerDistributor.retailer_id == retailer.id,
                RetailerDistributor.status == "approved",
            )
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
