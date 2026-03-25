"""Order management endpoints — history, detail, cancellation, invoices, mock advance."""
import logging
import uuid
from datetime import date, datetime, timezone
from decimal import Decimal

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import and_, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.api.deps import get_db, require_retailer
from app.auth.models import CurrentUser
from app.config import get_settings
from app.models.ordering import Invoice, Order, OrderLine, OrderLineItem
from app.models.retailer import Retailer
from app.schemas.ordering import (
    BackorderLineOut,
    BackordersPage,
    InvoiceOut,
    OrderOut,
    OrdersPage,
    OrderSummaryOut,
)

from app.api.v1.retailer import _get_or_create_retailer

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/orders", tags=["orders"])

_CANCELLABLE_ORDER_STATUSES = {"draft", "pending_transmission", "submitted"}
_CANCELLABLE_ITEM_STATUSES = {"pending", "back_ordered"}


# ─── Helpers ──────────────────────────────────────────────────────────────────

async def _get_order_for_retailer(
    db: AsyncSession, order_id: uuid.UUID, retailer: Retailer
) -> Order:
    order = (
        await db.execute(
            select(Order)
            .where(Order.id == order_id, Order.retailer_id == retailer.id)
            .options(selectinload(Order.lines).selectinload(OrderLine.items))
        )
    ).scalar_one_or_none()
    if not order:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Order not found")
    return order


def _order_summary(order: Order) -> OrderSummaryOut:
    return OrderSummaryOut(
        id=order.id,
        po_number=order.po_number,
        status=order.status,
        total_lines=order.total_lines,
        total_gbp=order.total_gbp,
        submitted_at=order.submitted_at,
        created_at=order.created_at,
    )


# ─── Endpoints ────────────────────────────────────────────────────────────────

@router.get("", response_model=OrdersPage)
async def list_orders(
    status_filter: str | None = None,
    from_date: date | None = None,
    to_date: date | None = None,
    distributor_code: str | None = None,
    page_size: int = 20,
    cursor: str | None = None,
    db: AsyncSession = Depends(get_db),
    current_user: CurrentUser = Depends(require_retailer),
) -> OrdersPage:
    """Order history with optional filters. Returns cursor-paginated summaries."""
    retailer = await _get_or_create_retailer(db, current_user)
    await db.commit()

    conditions = [Order.retailer_id == retailer.id]
    if status_filter:
        conditions.append(Order.status == status_filter)
    if from_date:
        conditions.append(Order.submitted_at >= datetime.combine(from_date, datetime.min.time()))
    if to_date:
        conditions.append(Order.submitted_at <= datetime.combine(to_date, datetime.max.time()))
    if cursor:
        try:
            conditions.append(Order.created_at < datetime.fromisoformat(cursor))
        except ValueError:
            pass

    q = (
        select(Order)
        .where(and_(*conditions))
        .order_by(Order.created_at.desc())
        .limit(page_size + 1)
    )

    # distributor_code filter requires a join — handled via subquery
    if distributor_code:
        from sqlalchemy import exists
        q = q.where(
            exists(
                select(OrderLine.id).where(
                    OrderLine.order_id == Order.id,
                    OrderLine.distributor_code == distributor_code,
                )
            )
        )

    orders = list((await db.execute(q)).scalars().all())
    next_cursor: str | None = None
    if len(orders) > page_size:
        orders = orders[:page_size]
        next_cursor = orders[-1].created_at.isoformat()

    return OrdersPage(
        orders=[_order_summary(o) for o in orders],
        next_cursor=next_cursor,
    )


@router.get("/backorders", response_model=BackordersPage)
async def list_backorders(
    distributor_code: str | None = None,
    from_date: date | None = None,
    to_date: date | None = None,
    page_size: int = 50,
    cursor: str | None = None,
    db: AsyncSession = Depends(get_db),
    current_user: CurrentUser = Depends(require_retailer),
) -> BackordersPage:
    """All active back-ordered line items across all orders."""
    retailer = await _get_or_create_retailer(db, current_user)
    await db.commit()

    conditions = [
        Order.retailer_id == retailer.id,
        OrderLineItem.status == "back_ordered",
    ]
    if distributor_code:
        conditions.append(OrderLine.distributor_code == distributor_code)
    if from_date:
        conditions.append(OrderLineItem.expected_despatch_date >= from_date)
    if to_date:
        conditions.append(OrderLineItem.expected_despatch_date <= to_date)
    if cursor:
        try:
            conditions.append(OrderLineItem.created_at < datetime.fromisoformat(cursor))
        except ValueError:
            pass

    rows = (
        await db.execute(
            select(Order.id, Order.po_number, OrderLine.id, OrderLine.distributor_code,
                   OrderLineItem.id, OrderLineItem.isbn13, OrderLineItem.quantity_ordered,
                   OrderLineItem.expected_despatch_date, OrderLineItem.created_at)
            .join(OrderLine, OrderLine.order_id == Order.id)
            .join(OrderLineItem, OrderLineItem.order_line_id == OrderLine.id)
            .where(and_(*conditions))
            .order_by(OrderLineItem.created_at.desc())
            .limit(page_size + 1)
        )
    ).all()

    next_cursor = None
    if len(rows) > page_size:
        rows = rows[:page_size]
        next_cursor = rows[-1][-1].isoformat()  # created_at of last item

    items = [
        BackorderLineOut(
            order_id=r[0], po_number=r[1], order_line_id=r[2],
            distributor_code=r[3], item_id=r[4], isbn13=r[5],
            quantity_ordered=r[6], expected_despatch_date=r[7],
        )
        for r in rows
    ]
    return BackordersPage(items=items, next_cursor=next_cursor)


@router.get("/{order_id}", response_model=OrderOut)
async def get_order(
    order_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    current_user: CurrentUser = Depends(require_retailer),
) -> OrderOut:
    """Full order detail with all lines and per-item statuses."""
    retailer = await _get_or_create_retailer(db, current_user)
    await db.commit()
    return await _get_order_for_retailer(db, order_id, retailer)


@router.delete("/{order_id}", status_code=status.HTTP_204_NO_CONTENT)
async def cancel_order(
    order_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    current_user: CurrentUser = Depends(require_retailer),
) -> None:
    """Cancel an entire order. Only allowed while status is draft, pending_transmission, or submitted."""
    retailer = await _get_or_create_retailer(db, current_user)
    await db.commit()
    order = await _get_order_for_retailer(db, order_id, retailer)

    if order.status not in _CANCELLABLE_ORDER_STATUSES:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=f"Order cannot be cancelled in status '{order.status}'. "
                   "Only draft, pending_transmission, or submitted orders can be cancelled.",
        )

    order.status = "cancelled"
    for line in order.lines:
        line.status = "cancelled"
        for item in line.items:
            if item.status in _CANCELLABLE_ITEM_STATUSES:
                item.status = "cancelled"
    await db.commit()


@router.delete("/{order_id}/lines/{line_id}", status_code=status.HTTP_204_NO_CONTENT)
async def cancel_order_line(
    order_id: uuid.UUID,
    line_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    current_user: CurrentUser = Depends(require_retailer),
) -> None:
    """Cancel all back-ordered items in a distributor line at once."""
    retailer = await _get_or_create_retailer(db, current_user)
    await db.commit()
    order = await _get_order_for_retailer(db, order_id, retailer)

    line = next((ln for ln in order.lines if ln.id == line_id), None)
    if not line:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Order line not found")

    cancellable = [i for i in line.items if i.status in _CANCELLABLE_ITEM_STATUSES]
    if not cancellable:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="No cancellable items in this line. "
                   "Only back_ordered or pending items can be cancelled.",
        )

    for item in cancellable:
        item.status = "cancelled"

    # If all items in the line are now cancelled, mark the line too
    if all(i.status == "cancelled" for i in line.items):
        line.status = "cancelled"

    await db.commit()


@router.delete("/{order_id}/lines/{line_id}/items/{item_id}",
               status_code=status.HTTP_204_NO_CONTENT)
async def cancel_line_item(
    order_id: uuid.UUID,
    line_id: uuid.UUID,
    item_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    current_user: CurrentUser = Depends(require_retailer),
) -> None:
    """Cancel a single back-ordered item."""
    retailer = await _get_or_create_retailer(db, current_user)
    await db.commit()
    order = await _get_order_for_retailer(db, order_id, retailer)

    line = next((ln for ln in order.lines if ln.id == line_id), None)
    if not line:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Order line not found")

    item = next((i for i in line.items if i.id == item_id), None)
    if not item:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Item not found")

    if item.status not in _CANCELLABLE_ITEM_STATUSES:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=f"Item cannot be cancelled in status '{item.status}'. "
                   "Only back_ordered or pending items can be cancelled.",
        )

    item.status = "cancelled"
    if all(i.status == "cancelled" for i in line.items):
        line.status = "cancelled"
    await db.commit()


# ─── Invoice ──────────────────────────────────────────────────────────────────

@router.get("/{order_id}/invoice", response_model=InvoiceOut)
async def get_invoice(
    order_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    current_user: CurrentUser = Depends(require_retailer),
) -> InvoiceOut:
    """Retrieve invoice for an order. Available once any order line reaches 'invoiced' status."""
    retailer = await _get_or_create_retailer(db, current_user)
    await db.commit()
    order = await _get_order_for_retailer(db, order_id, retailer)

    invoiced_line = next((ln for ln in order.lines if ln.status == "invoiced"), None)
    if not invoiced_line:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="No invoice available yet. Invoice is created once the order has been invoiced "
                   "by the distributor.",
        )

    invoice = (
        await db.execute(
            select(Invoice).where(Invoice.order_line_id == invoiced_line.id)
        )
    ).scalar_one_or_none()

    if not invoice:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND,
                            detail="Invoice record not found")
    return invoice


# ─── Mock status advancement (dev/demo only) ──────────────────────────────────

@router.post("/{order_id}/_advance", response_model=OrderOut)
async def advance_mock_order(
    order_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    current_user: CurrentUser = Depends(require_retailer),
) -> OrderOut:
    """DEV/DEMO ONLY — advance a mock order to its next status stage.

    Env-gated: requires ENABLE_MOCK_ADVANCE=true.
    Sequence: submitted → acknowledged → partially_despatched → fully_despatched → invoiced
    """
    settings = get_settings()
    if not getattr(settings, "enable_mock_advance", False):
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Not found",  # Intentionally opaque — not advertised in production
        )

    retailer = await _get_or_create_retailer(db, current_user)
    await db.commit()
    order = await _get_order_for_retailer(db, order_id, retailer)

    # Only works for mock connector orders
    non_mock = [ln for ln in order.lines if ln.distributor_code.upper() != "MOCK"]
    if non_mock:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Mock advance only works for orders placed via the mock connector",
        )

    today = datetime.now(timezone.utc).date()
    _advance_order_status(order, today)

    await db.commit()

    order_fresh = (
        await db.execute(
            select(Order)
            .where(Order.id == order.id)
            .options(selectinload(Order.lines).selectinload(OrderLine.items))
        )
    ).scalar_one()
    return order_fresh


def _advance_order_status(order: Order, today: date) -> None:
    """In-place mutation: advance order + lines + items to next stage."""
    from app.models.ordering import Invoice

    if order.status in ("pending_transmission", "submitted"):
        # → acknowledged: set per-item statuses
        order.status = "acknowledged"
        for line in order.lines:
            line.status = "acknowledged"
            for i, item in enumerate(line.items):
                # Deterministic mock: even index = confirmed, odd = back_ordered
                if i % 3 == 2:
                    item.status = "back_ordered"
                    item.expected_despatch_date = date(today.year, today.month, today.day)
                else:
                    item.status = "confirmed"
                    item.quantity_confirmed = item.quantity_ordered

    elif order.status == "acknowledged":
        # → despatched: mark confirmed items as despatched
        order.status = "partially_despatched"
        for line in order.lines:
            confirmed = [i for i in line.items if i.status == "confirmed"]
            for item in confirmed:
                item.status = "despatched"
                item.quantity_despatched = item.quantity_confirmed
            if all(i.status in ("despatched", "back_ordered", "cancelled") for i in line.items):
                line.status = "partially_despatched"
                line.tracking_ref = f"MOCK-TRACK-{str(line.id)[:8].upper()}"

    elif order.status == "partially_despatched":
        # → fully despatched: mark all despatched
        order.status = "fully_despatched"
        for line in order.lines:
            for item in line.items:
                if item.status in ("confirmed", "despatched"):
                    item.status = "despatched"
                    item.quantity_despatched = item.quantity_confirmed or item.quantity_ordered
            line.status = "fully_despatched"

    elif order.status == "fully_despatched":
        # → invoiced: create invoice records
        order.status = "invoiced"
        for line in order.lines:
            line.status = "invoiced"
            for item in line.items:
                if item.status == "despatched":
                    item.status = "invoiced"
                    item.quantity_invoiced = item.quantity_despatched
            # Create invoice if not already present
            if not line.invoice:
                subtotal = line.subtotal_gbp or Decimal("0")
                vat = (subtotal * Decimal("0.20")).quantize(Decimal("0.01"))
                line.invoice = Invoice(
                    order_line_id=line.id,
                    invoice_number=f"MOCK-INV-{str(line.id)[:8].upper()}",
                    invoice_date=today,
                    net_gbp=subtotal,
                    vat_gbp=vat,
                    gross_gbp=subtotal + vat,
                )
