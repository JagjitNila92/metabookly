"""Retailer settings and address book endpoints."""
import uuid
import logging

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_db, require_retailer
from app.auth.models import CurrentUser
from app.models.ordering import RetailerAddress, RetailerSettings
from app.schemas.ordering import (
    AddressCreate,
    AddressOut,
    AddressUpdate,
    RetailerSettingsOut,
    RetailerSettingsUpdate,
)
from app.api.v1.retailer import _get_or_create_retailer

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/retailer", tags=["retailer"])


# ─── Settings helpers ─────────────────────────────────────────────────────────

async def _get_or_create_settings(db, retailer_id: uuid.UUID) -> RetailerSettings:
    settings = (
        await db.execute(
            select(RetailerSettings).where(RetailerSettings.retailer_id == retailer_id)
        )
    ).scalar_one_or_none()
    if settings is None:
        settings = RetailerSettings(retailer_id=retailer_id)
        db.add(settings)
        await db.flush()
    return settings


# ─── Settings endpoints ───────────────────────────────────────────────────────

@router.get("/settings", response_model=RetailerSettingsOut)
async def get_settings(
    db: AsyncSession = Depends(get_db),
    current_user: CurrentUser = Depends(require_retailer),
) -> RetailerSettingsOut:
    """Return notification settings. Auto-creates defaults on first access."""
    retailer = await _get_or_create_retailer(db, current_user)
    settings = await _get_or_create_settings(db, retailer.id)
    await db.commit()
    return settings


@router.patch("/settings", response_model=RetailerSettingsOut)
async def update_settings(
    body: RetailerSettingsUpdate,
    db: AsyncSession = Depends(get_db),
    current_user: CurrentUser = Depends(require_retailer),
) -> RetailerSettingsOut:
    """Update notification toggles. Only provided fields are changed."""
    retailer = await _get_or_create_retailer(db, current_user)
    settings = await _get_or_create_settings(db, retailer.id)

    if body.notify_order_submitted is not None:
        settings.notify_order_submitted = body.notify_order_submitted
    if body.notify_backorder_alert is not None:
        settings.notify_backorder_alert = body.notify_backorder_alert
    if body.notify_invoice_available is not None:
        settings.notify_invoice_available = body.notify_invoice_available

    await db.commit()
    await db.refresh(settings)
    return settings


# ─── Address endpoints ────────────────────────────────────────────────────────

@router.get("/addresses", response_model=list[AddressOut])
async def list_addresses(
    address_type: str | None = None,
    db: AsyncSession = Depends(get_db),
    current_user: CurrentUser = Depends(require_retailer),
) -> list[AddressOut]:
    """List all addresses. Filter by ?address_type=billing or delivery."""
    retailer = await _get_or_create_retailer(db, current_user)
    await db.commit()

    conditions = [RetailerAddress.retailer_id == retailer.id]
    if address_type:
        conditions.append(RetailerAddress.address_type == address_type)

    addresses = list(
        (
            await db.execute(
                select(RetailerAddress)
                .where(*conditions)
                .order_by(RetailerAddress.is_default.desc(), RetailerAddress.created_at)
            )
        ).scalars().all()
    )
    return addresses


@router.post("/addresses", response_model=AddressOut, status_code=status.HTTP_201_CREATED)
async def create_address(
    body: AddressCreate,
    db: AsyncSession = Depends(get_db),
    current_user: CurrentUser = Depends(require_retailer),
) -> AddressOut:
    """Add a billing or delivery address to the address book."""
    retailer = await _get_or_create_retailer(db, current_user)

    # If new address is_default, clear other defaults of the same type
    if body.is_default:
        existing_defaults = list(
            (
                await db.execute(
                    select(RetailerAddress).where(
                        RetailerAddress.retailer_id == retailer.id,
                        RetailerAddress.address_type == body.address_type,
                        RetailerAddress.is_default.is_(True),
                    )
                )
            ).scalars().all()
        )
        for addr in existing_defaults:
            addr.is_default = False

    address = RetailerAddress(retailer_id=retailer.id, **body.model_dump())
    db.add(address)
    await db.commit()
    await db.refresh(address)
    return address


@router.patch("/addresses/{address_id}", response_model=AddressOut)
async def update_address(
    address_id: uuid.UUID,
    body: AddressUpdate,
    db: AsyncSession = Depends(get_db),
    current_user: CurrentUser = Depends(require_retailer),
) -> AddressOut:
    """Update an address. Only provided fields are changed."""
    retailer = await _get_or_create_retailer(db, current_user)

    address = (
        await db.execute(
            select(RetailerAddress).where(
                RetailerAddress.id == address_id,
                RetailerAddress.retailer_id == retailer.id,
            )
        )
    ).scalar_one_or_none()
    if not address:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Address not found")

    updates = body.model_dump(exclude_unset=True)

    # If setting as default, clear other defaults first
    if updates.get("is_default"):
        existing_defaults = list(
            (
                await db.execute(
                    select(RetailerAddress).where(
                        RetailerAddress.retailer_id == retailer.id,
                        RetailerAddress.address_type == address.address_type,
                        RetailerAddress.is_default.is_(True),
                        RetailerAddress.id != address_id,
                    )
                )
            ).scalars().all()
        )
        for addr in existing_defaults:
            addr.is_default = False

    for field, value in updates.items():
        setattr(address, field, value)

    await db.commit()
    await db.refresh(address)
    return address


@router.delete("/addresses/{address_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_address(
    address_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    current_user: CurrentUser = Depends(require_retailer),
) -> None:
    """Remove an address from the address book."""
    retailer = await _get_or_create_retailer(db, current_user)

    address = (
        await db.execute(
            select(RetailerAddress).where(
                RetailerAddress.id == address_id,
                RetailerAddress.retailer_id == retailer.id,
            )
        )
    ).scalar_one_or_none()
    if not address:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Address not found")

    await db.delete(address)
    await db.commit()
