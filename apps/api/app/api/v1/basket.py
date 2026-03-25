"""Basket endpoints — add/update/remove items, routing, submission."""
import logging
import uuid

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.api.deps import get_db, require_retailer
from app.auth.models import CurrentUser
from app.models.basket import Basket, BasketItem
from app.models.book import Book
from app.models.retailer import Retailer
from app.schemas.ordering import (
    BasketItemAdd,
    BasketItemUpdate,
    BasketOut,
    OrderOut,
    SubmitBasketRequest,
)
from app.services.basket_service import build_basket_out, get_or_create_basket, submit_basket

# Reuse _get_or_create_retailer from retailer endpoint
from app.api.v1.retailer import _get_or_create_retailer

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/basket", tags=["basket"])


async def _get_basket(db: AsyncSession, retailer: Retailer) -> Basket:
    basket = (
        await db.execute(
            select(Basket)
            .where(Basket.retailer_id == retailer.id)
            .options(selectinload(Basket.items))
        )
    ).scalar_one_or_none()
    if basket is None:
        basket = Basket(retailer_id=retailer.id)
        db.add(basket)
        await db.flush()
        # Re-query with selectinload to avoid lazy-load in async context
        basket = (
            await db.execute(
                select(Basket)
                .where(Basket.id == basket.id)
                .options(selectinload(Basket.items))
            )
        ).scalar_one()
    return basket


# ─── Endpoints ────────────────────────────────────────────────────────────────

@router.get("", response_model=BasketOut)
async def get_basket(
    db: AsyncSession = Depends(get_db),
    current_user: CurrentUser = Depends(require_retailer),
) -> BasketOut:
    """Return the active basket with routing and margin data."""
    retailer = await _get_or_create_retailer(db, current_user)
    await db.commit()
    basket = await _get_basket(db, retailer)
    return await build_basket_out(db, basket, retailer)


@router.post("/items", response_model=BasketOut, status_code=status.HTTP_201_CREATED)
async def add_item(
    body: BasketItemAdd,
    db: AsyncSession = Depends(get_db),
    current_user: CurrentUser = Depends(require_retailer),
) -> BasketOut:
    """Add a book to the basket. Increments quantity if already present."""
    retailer = await _get_or_create_retailer(db, current_user)

    book = (
        await db.execute(select(Book).where(Book.isbn13 == body.isbn13))
    ).scalar_one_or_none()
    if not book:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND,
                            detail=f"ISBN {body.isbn13} not found in catalog")

    basket = await _get_basket(db, retailer)

    existing = next((i for i in basket.items if i.isbn13 == body.isbn13), None)
    if existing:
        existing.quantity += body.quantity
        if body.preferred_distributor_code is not None:
            existing.preferred_distributor_code = body.preferred_distributor_code
    else:
        item = BasketItem(
            basket_id=basket.id,
            book_id=book.id,
            isbn13=body.isbn13,
            quantity=body.quantity,
            preferred_distributor_code=body.preferred_distributor_code,
        )
        db.add(item)
        basket.items.append(item)

    await db.commit()
    basket = await _get_basket(db, retailer)
    return await build_basket_out(db, basket, retailer)


@router.patch("/items/{isbn13}", response_model=BasketOut)
async def update_item(
    isbn13: str,
    body: BasketItemUpdate,
    db: AsyncSession = Depends(get_db),
    current_user: CurrentUser = Depends(require_retailer),
) -> BasketOut:
    """Update quantity or preferred distributor for a basket item."""
    retailer = await _get_or_create_retailer(db, current_user)
    basket = await _get_basket(db, retailer)

    item = next((i for i in basket.items if i.isbn13 == isbn13), None)
    if not item:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND,
                            detail=f"{isbn13} is not in your basket")

    if body.quantity is not None:
        item.quantity = body.quantity
    if body.preferred_distributor_code is not None:
        item.preferred_distributor_code = body.preferred_distributor_code

    await db.commit()
    basket = await _get_basket(db, retailer)
    return await build_basket_out(db, basket, retailer)


@router.delete("/items/{isbn13}", response_model=BasketOut)
async def remove_item(
    isbn13: str,
    db: AsyncSession = Depends(get_db),
    current_user: CurrentUser = Depends(require_retailer),
) -> BasketOut:
    """Remove a single item from the basket."""
    retailer = await _get_or_create_retailer(db, current_user)
    basket = await _get_basket(db, retailer)

    item = next((i for i in basket.items if i.isbn13 == isbn13), None)
    if not item:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND,
                            detail=f"{isbn13} is not in your basket")

    await db.delete(item)
    await db.commit()
    basket = await _get_basket(db, retailer)
    return await build_basket_out(db, basket, retailer)


@router.delete("", status_code=status.HTTP_204_NO_CONTENT)
async def clear_basket(
    db: AsyncSession = Depends(get_db),
    current_user: CurrentUser = Depends(require_retailer),
) -> None:
    """Clear all items from the basket."""
    retailer = await _get_or_create_retailer(db, current_user)
    basket = await _get_basket(db, retailer)
    for item in list(basket.items):
        await db.delete(item)
    basket.items.clear()
    await db.commit()


@router.get("/route", response_model=BasketOut)
async def refresh_routing(
    db: AsyncSession = Depends(get_db),
    current_user: CurrentUser = Depends(require_retailer),
) -> BasketOut:
    """Re-run routing with fresh live prices from distributors."""
    retailer = await _get_or_create_retailer(db, current_user)
    await db.commit()
    basket = await _get_basket(db, retailer)
    return await build_basket_out(db, basket, retailer)


@router.post("/submit", response_model=OrderOut, status_code=status.HTTP_201_CREATED)
async def submit_order(
    body: SubmitBasketRequest,
    db: AsyncSession = Depends(get_db),
    current_user: CurrentUser = Depends(require_retailer),
) -> OrderOut:
    """Submit the basket as an order.

    Creates Order + OrderLines, transmits to distributors, clears the basket.
    Returns the full Order with initial per-line statuses so the confirmation
    screen can render immediately without a second request.
    """
    retailer = await _get_or_create_retailer(db, current_user)
    await db.commit()
    basket = await _get_basket(db, retailer)

    order = await submit_basket(
        db=db,
        basket=basket,
        retailer=retailer,
        delivery_address_id=body.delivery_address_id,
        delivery_address=body.delivery_address,
        billing_address_id=body.billing_address_id,
    )
    return order
