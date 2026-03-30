"""
Distributor-facing endpoints for managing retailer account link requests.

For the MVP these are admin-gated. When distributor Cognito users are introduced,
the require_admin dependency can be swapped for a require_distributor that also
checks the distributor_code matches the user's assigned distributor.
"""
import logging
import uuid

from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException, Query, status
from sqlalchemy import select
from sqlalchemy.orm import selectinload
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_db, require_admin
from app.auth.models import CurrentUser
from app.connectors.registry import get_connector
from app.models.ordering import Order, OrderLine, OrderLineItem
from app.models.retailer import Retailer, RetailerDistributor
from app.schemas.retailer import AccountRequestOut, ApproveRequest, ReviewRequest, RetailerSummary
from app.services.email_service import (
    notify_retailer_request_approved,
    notify_retailer_request_rejected,
)

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/distributor", tags=["distributor"])


def _distributor_name(code: str) -> str:
    try:
        return get_connector(code).distributor_name
    except ValueError:
        return code


def _request_out(account: RetailerDistributor) -> AccountRequestOut:
    return AccountRequestOut(
        id=account.id,
        distributor_code=account.distributor_code,
        distributor_name=_distributor_name(account.distributor_code),
        account_number=account.account_number,
        status=account.status,
        rejection_reason=account.rejection_reason,
        gratis_enabled=account.gratis_enabled,
        retailer=RetailerSummary(
            id=account.retailer.id,
            company_name=account.retailer.company_name,
            email=account.retailer.email,
        ),
        created_at=account.created_at,
        updated_at=account.updated_at,
    )


@router.get("/requests", response_model=list[AccountRequestOut])
async def list_requests(
    status_filter: str | None = Query(None, alias="status"),
    db: AsyncSession = Depends(get_db),
    _: CurrentUser = Depends(require_admin),
) -> list[AccountRequestOut]:
    """
    List all retailer account link requests, optionally filtered by status.
    Defaults to showing pending requests only.
    """
    effective_status = status_filter or "pending"
    rows = (
        await db.execute(
            select(RetailerDistributor)
            .options(selectinload(RetailerDistributor.retailer))
            .where(RetailerDistributor.status == effective_status)
            .order_by(RetailerDistributor.created_at)
        )
    ).scalars().all()

    return [_request_out(r) for r in rows]


@router.post("/requests/{request_id}/approve", response_model=AccountRequestOut)
async def approve_request(
    request_id: uuid.UUID,
    body: ApproveRequest,
    background_tasks: BackgroundTasks,
    db: AsyncSession = Depends(get_db),
    _: CurrentUser = Depends(require_admin),
) -> AccountRequestOut:
    """Approve a pending account link request. Optionally enable gratis ordering."""
    account = (
        await db.execute(
            select(RetailerDistributor)
            .options(selectinload(RetailerDistributor.retailer))
            .where(RetailerDistributor.id == request_id)
        )
    ).scalar_one_or_none()

    if not account:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Request not found")
    if account.status != "pending":
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=f"Request is already {account.status}",
        )

    account.status = "approved"
    account.rejection_reason = None
    account.gratis_enabled = body.gratis_enabled
    await db.commit()
    await db.refresh(account)

    logger.info(
        "Approved account link: retailer=%s distributor=%s",
        account.retailer.email,
        account.distributor_code,
    )
    background_tasks.add_task(
        notify_retailer_request_approved,
        retailer_email=account.retailer.email,
        retailer_company=account.retailer.company_name,
        distributor_name=_distributor_name(account.distributor_code),
        account_number=account.account_number,
    )
    return _request_out(account)


@router.post("/requests/{request_id}/reject", response_model=AccountRequestOut)
async def reject_request(
    request_id: uuid.UUID,
    body: ReviewRequest,
    background_tasks: BackgroundTasks,
    db: AsyncSession = Depends(get_db),
    _: CurrentUser = Depends(require_admin),
) -> AccountRequestOut:
    """Reject a pending account link request, with an optional reason."""
    account = (
        await db.execute(
            select(RetailerDistributor)
            .options(selectinload(RetailerDistributor.retailer))
            .where(RetailerDistributor.id == request_id)
        )
    ).scalar_one_or_none()

    if not account:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Request not found")
    if account.status != "pending":
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=f"Request is already {account.status}",
        )

    account.status = "rejected"
    account.rejection_reason = body.rejection_reason
    await db.commit()
    await db.refresh(account)

    logger.info(
        "Rejected account link: retailer=%s distributor=%s reason=%s",
        account.retailer.email,
        account.distributor_code,
        body.rejection_reason,
    )
    background_tasks.add_task(
        notify_retailer_request_rejected,
        retailer_email=account.retailer.email,
        retailer_company=account.retailer.company_name,
        distributor_name=_distributor_name(account.distributor_code),
        account_number=account.account_number,
        rejection_reason=body.rejection_reason,
    )
    return _request_out(account)


# ─── Distributor orders view ───────────────────────────────────────────────────

@router.get("/orders")
async def list_distributor_orders(
    distributor_code: str = Query(...),
    order_type: str | None = Query(None),
    status_filter: str | None = Query(None, alias="status"),
    cursor: str | None = Query(None),
    db: AsyncSession = Depends(get_db),
    _: CurrentUser = Depends(require_admin),
) -> dict:
    """
    List all order lines sent to a given distributor, newest first.
    Returns order + retailer context alongside each line's items.
    """
    from sqlalchemy.orm import selectinload
    PAGE = 25

    stmt = (
        select(OrderLine)
        .join(Order, Order.id == OrderLine.order_id)
        .join(Retailer, Retailer.id == Order.retailer_id)
        .options(selectinload(OrderLine.items))
        .where(OrderLine.distributor_code == distributor_code.upper())
    )

    if order_type:
        stmt = stmt.where(Order.order_type == order_type)
    if status_filter:
        stmt = stmt.where(OrderLine.status == status_filter)
    if cursor:
        from datetime import datetime as dt
        try:
            cursor_dt = dt.fromisoformat(cursor)
            stmt = stmt.where(Order.submitted_at < cursor_dt)
        except ValueError:
            pass

    stmt = stmt.order_by(Order.submitted_at.desc()).limit(PAGE + 1)
    lines = (await db.execute(stmt)).scalars().all()
    has_more = len(lines) > PAGE
    lines = lines[:PAGE]

    order_ids = list({l.order_id for l in lines})
    orders_map: dict = {}
    retailers_map: dict = {}
    if order_ids:
        order_rows = (await db.execute(select(Order).where(Order.id.in_(order_ids)))).scalars().all()
        for o in order_rows:
            orders_map[o.id] = o
        retailer_ids = list({o.retailer_id for o in order_rows})
        retailer_rows = (await db.execute(select(Retailer).where(Retailer.id.in_(retailer_ids)))).scalars().all()
        for r in retailer_rows:
            retailers_map[r.id] = r

    from app.models.book import Book
    isbn_set = {i.isbn13 for l in lines for i in l.items}
    titles_map: dict[str, str] = {}
    if isbn_set:
        book_rows = (await db.execute(select(Book.isbn13, Book.title).where(Book.isbn13.in_(isbn_set)))).all()
        titles_map = {r.isbn13: r.title for r in book_rows}

    result = []
    for line in lines:
        order = orders_map.get(line.order_id)
        if not order:
            continue
        retailer = retailers_map.get(order.retailer_id)
        result.append({
            "order_line_id": str(line.id),
            "order_id": str(order.id),
            "po_number": order.po_number,
            "order_type": order.order_type,
            "order_status": order.status,
            "line_status": line.status,
            "submitted_at": order.submitted_at.isoformat() if order.submitted_at else None,
            "retailer_company": retailer.company_name if retailer else "Unknown",
            "subtotal_gbp": str(line.subtotal_gbp) if line.subtotal_gbp is not None else None,
            "items": [
                {
                    "isbn13": i.isbn13,
                    "title": titles_map.get(i.isbn13),
                    "quantity_ordered": i.quantity_ordered,
                    "quantity_confirmed": i.quantity_confirmed,
                    "status": i.status,
                    "trade_price_gbp": str(i.trade_price_gbp) if i.trade_price_gbp is not None else None,
                }
                for i in line.items
            ],
        })

    next_cursor = None
    if has_more and result:
        next_cursor = result[-1]["submitted_at"]

    return {"orders": result, "next_cursor": next_cursor}
