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
