"""Basket service — routing and order submission logic."""
import logging
import uuid
from datetime import datetime, timezone
from decimal import Decimal

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.aws.secrets import get_retailer_distributor_credentials
from app.connectors.registry import get_connector
from app.models.basket import Basket, BasketItem
from app.models.book import Book
from app.models.ordering import Order, OrderLine, OrderLineItem, RetailerAddress
from app.models.retailer import Retailer, RetailerDistributor
from app.schemas.ordering import (
    AddressIn,
    BackorderLineOut,
    BasketOut,
    OrderLineItemOut,
    OrderLineOut,
    OrderOut,
    RoutedItemOut,
)

logger = logging.getLogger(__name__)

# ─── PO number generation ─────────────────────────────────────────────────────

async def _next_po_number(db: AsyncSession, retailer: Retailer) -> str:
    """Generate next PO number: MB-{prefix}-{YYYYMMDD}-{seq}."""
    from sqlalchemy import func as sqlfunc
    today = datetime.now(timezone.utc).strftime("%Y%m%d")
    prefix = "".join(c for c in (retailer.company_name or "MB")[:4].upper() if c.isalpha()) or "MB"
    prefix = prefix[:4]
    pattern = f"MB-{prefix}-{today}-%"
    count = (
        await db.execute(
            select(sqlfunc.count()).where(Order.po_number.like(pattern))
        )
    ).scalar() or 0
    return f"MB-{prefix}-{today}-{count + 1:03d}"


# ─── Basket retrieval ─────────────────────────────────────────────────────────

async def get_or_create_basket(db: AsyncSession, retailer: Retailer) -> Basket:
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
        basket = (
            await db.execute(
                select(Basket)
                .where(Basket.id == basket.id)
                .options(selectinload(Basket.items))
            )
        ).scalar_one()
    return basket


async def _active_accounts(
    db: AsyncSession, retailer: Retailer
) -> list[RetailerDistributor]:
    return list(
        (
            await db.execute(
                select(RetailerDistributor).where(
                    RetailerDistributor.retailer_id == retailer.id,
                    RetailerDistributor.status == "approved",
                )
            )
        ).scalars().all()
    )


# ─── Routing ──────────────────────────────────────────────────────────────────

async def _route_item(
    item: BasketItem,
    accounts: list[RetailerDistributor],
    retailer: Retailer,
) -> tuple[str | None, Decimal | None, Decimal | None]:
    """Return (routed_distributor_code, trade_price_gbp, rrp_gbp) for an item.

    For MVP: if preferred_distributor_code is set and account is active, use it.
    Otherwise pick the first active account that returns availability.
    Silently falls back to None if no account can supply.
    """
    if not accounts:
        return None, None, None

    candidates: list[RetailerDistributor] = []
    if item.preferred_distributor_code:
        preferred = next(
            (a for a in accounts if a.distributor_code == item.preferred_distributor_code), None
        )
        if preferred:
            candidates = [preferred]

    if not candidates:
        candidates = accounts

    for account in candidates:
        try:
            connector = get_connector(account.distributor_code)
            creds = (
                get_retailer_distributor_credentials(
                    retailer_id=str(retailer.id),
                    distributor_code=account.distributor_code,
                )
                if connector.requires_credentials
                else {}
            )
            result = await connector.get_price_availability(item.isbn13, creds)
            if result.available:
                trade_price = Decimal(str(result.price_gbp)) if result.price_gbp else None
                return account.distributor_code, trade_price, None  # rrp_gbp fetched from book below
        except Exception as e:
            logger.warning("Routing check failed for %s via %s: %s",
                           item.isbn13, account.distributor_code, e)

    return None, None, None


async def build_basket_out(
    db: AsyncSession, basket: Basket, retailer: Retailer
) -> BasketOut:
    """Build a fully-routed BasketOut response."""
    accounts = await _active_accounts(db, retailer)
    routed: list[RoutedItemOut] = []

    for item in basket.items:
        book = (
            await db.execute(select(Book).where(Book.id == item.book_id))
        ).scalar_one_or_none()

        dist_code, trade_price, _ = await _route_item(item, accounts, retailer)
        rrp = book.rrp_gbp if book else None

        margin: Decimal | None = None
        if trade_price is not None and rrp and rrp > 0:
            margin = ((rrp - trade_price) / rrp * 100).quantize(Decimal("0.01"))

        routed.append(RoutedItemOut(
            isbn13=item.isbn13,
            title=book.title if book else None,
            cover_image_url=book.cover_image_url if book else None,
            quantity=item.quantity,
            preferred_distributor_code=item.preferred_distributor_code,
            routed_distributor_code=dist_code,
            trade_price_gbp=trade_price,
            rrp_gbp=rrp,
            margin_pct=margin,
        ))

    total_cost: Decimal | None = None
    supplied = [r for r in routed if r.trade_price_gbp is not None]
    if supplied:
        total_cost = sum(
            r.trade_price_gbp * r.quantity for r in supplied
        )

    avg_margin: Decimal | None = None
    margined = [r for r in routed if r.margin_pct is not None]
    if margined:
        avg_margin = (sum(r.margin_pct for r in margined) / len(margined)).quantize(
            Decimal("0.01")
        )

    return BasketOut(
        item_count=len(basket.items),
        total_cost_gbp=total_cost,
        avg_margin_pct=avg_margin,
        items=routed,
    )


# ─── Order submission ─────────────────────────────────────────────────────────

async def submit_basket(
    db: AsyncSession,
    basket: Basket,
    retailer: Retailer,
    delivery_address_id: uuid.UUID | None,
    delivery_address: AddressIn | None,
    billing_address_id: uuid.UUID | None,
) -> Order:
    """Submit the basket: create Order + OrderLines, transmit to connectors, clear basket."""
    if not basket.items:
        from fastapi import HTTPException, status
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Basket is empty")

    accounts = await _active_accounts(db, retailer)
    if not accounts:
        from fastapi import HTTPException, status
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="No active distributor accounts — link and get approved before ordering",
        )

    # Resolve delivery address snapshot
    snapshot: dict | None = None
    if delivery_address_id:
        addr = (
            await db.execute(
                select(RetailerAddress).where(
                    RetailerAddress.id == delivery_address_id,
                    RetailerAddress.retailer_id == retailer.id,
                )
            )
        ).scalar_one_or_none()
        if not addr:
            from fastapi import HTTPException, status
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST,
                                detail="delivery_address_id not found")
        snapshot = {
            "contact_name": addr.contact_name, "line1": addr.line1, "line2": addr.line2,
            "city": addr.city, "county": addr.county, "postcode": addr.postcode,
            "country_code": addr.country_code,
        }
    elif delivery_address:
        snapshot = delivery_address.model_dump()

    po_number = await _next_po_number(db, retailer)

    order = Order(
        retailer_id=retailer.id,
        po_number=po_number,
        status="pending_transmission",
        billing_address_id=billing_address_id,
        delivery_address_id=delivery_address_id,
        delivery_address_snapshot=snapshot,
        submitted_at=datetime.now(timezone.utc).replace(tzinfo=None),
    )
    db.add(order)
    await db.flush()

    # Group items by routed distributor
    groups: dict[str, list[tuple[BasketItem, Decimal | None, Decimal | None]]] = {}
    unroutable: list[str] = []

    for item in basket.items:
        dist_code, trade_price, _ = await _route_item(item, accounts, retailer)
        if dist_code is None:
            unroutable.append(item.isbn13)
            continue
        book = (await db.execute(select(Book).where(Book.id == item.book_id))).scalar_one_or_none()
        rrp = book.rrp_gbp if book else None
        groups.setdefault(dist_code, []).append((item, trade_price, rrp))

    if not groups:
        from fastapi import HTTPException, status
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"No items could be routed to an active distributor. Unroutable: {unroutable}",
        )

    # Create order lines per distributor
    for seq, (dist_code, items) in enumerate(groups.items(), start=1):
        line = OrderLine(
            order_id=order.id,
            distributor_code=dist_code,
            status="pending",
        )
        db.add(line)
        await db.flush()

        subtotal = Decimal("0")
        for item_seq, (item, trade_price, rrp) in enumerate(items, start=1):
            ref = f"{str(line.id)[:8]}-{item_seq:03d}"
            li = OrderLineItem(
                order_line_id=line.id,
                book_id=item.book_id,
                isbn13=item.isbn13,
                retailer_line_ref=ref,
                quantity_ordered=item.quantity,
                status="pending",
                trade_price_gbp=trade_price,
                rrp_gbp=rrp,
            )
            db.add(li)
            if trade_price:
                subtotal += trade_price * item.quantity

        line.subtotal_gbp = subtotal if subtotal else None

    order.total_lines = len(groups)
    order.total_gbp = sum(
        (g[1] or Decimal("0")) * g[0].quantity
        for items_list in groups.values()
        for g in items_list
        if g[1]
    ) or None

    # Transmit to each connector (mock: instant response)
    await _transmit_order(db, order, groups, retailer, accounts)

    # Clear basket
    for item in list(basket.items):
        await db.delete(item)

    await db.commit()
    await db.refresh(order)

    # Eager-load lines + items for response
    order_fresh = (
        await db.execute(
            select(Order)
            .where(Order.id == order.id)
            .options(
                selectinload(Order.lines).selectinload(OrderLine.items)
            )
        )
    ).scalar_one()
    return order_fresh


async def _transmit_order(
    db: AsyncSession,
    order: Order,
    groups: dict,
    retailer: Retailer,
    accounts: list[RetailerDistributor],
) -> None:
    """Transmit each order_line to its connector. Mock connector responds instantly."""
    from sqlalchemy import select as sa_select
    lines = (
        await db.execute(
            select(OrderLine)
            .where(OrderLine.order_id == order.id)
            .options(selectinload(OrderLine.items))
        )
    ).scalars().all()

    for line in lines:
        account = next((a for a in accounts if a.distributor_code == line.distributor_code), None)
        if not account:
            line.status = "transmission_failed"
            continue
        try:
            connector = get_connector(line.distributor_code)
            creds = (
                get_retailer_distributor_credentials(
                    retailer_id=str(retailer.id),
                    distributor_code=line.distributor_code,
                )
                if connector.requires_credentials
                else {}
            )
            # For MVP mock connector: place order returns per-item statuses
            if hasattr(connector, "place_order"):
                item_data = [
                    {"isbn13": i.isbn13, "quantity": i.quantity_ordered,
                     "retailer_line_ref": i.retailer_line_ref}
                    for i in line.items
                ]
                result = await connector.place_order(
                    order_id=str(order.id),
                    po_number=order.po_number,
                    items=item_data,
                    credentials=creds,
                )
                line.status = result.get("line_status", "submitted")
                line.transmission_attempts = 1
                line.last_attempted_at = datetime.now(timezone.utc).replace(tzinfo=None)
                for item in line.items:
                    item_result = result.get("items", {}).get(item.retailer_line_ref, {})
                    item.status = item_result.get("status", "confirmed")
                    item.quantity_confirmed = item_result.get("quantity_confirmed",
                                                              item.quantity_ordered)
                    item.expected_despatch_date = item_result.get("expected_despatch_date")
            else:
                # Connector doesn't support place_order yet — mark submitted
                line.status = "submitted"
                line.transmission_attempts = 1
                line.last_attempted_at = datetime.now(timezone.utc).replace(tzinfo=None)
                for item in line.items:
                    item.status = "confirmed"
                    item.quantity_confirmed = item.quantity_ordered

        except Exception as e:
            logger.error("Transmission failed for order_line %s: %s", line.id, e)
            line.status = "transmission_failed"
            line.transmission_attempts = (line.transmission_attempts or 0) + 1
            line.last_attempted_at = datetime.now(timezone.utc).replace(tzinfo=None)

    # Roll up order status
    line_statuses = {ln.status for ln in lines}
    if "transmission_failed" in line_statuses and len(line_statuses) == 1:
        order.status = "transmission_failed"
    else:
        order.status = "acknowledged"
