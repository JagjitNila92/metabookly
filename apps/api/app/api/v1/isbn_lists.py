"""Saved ISBN list endpoints — create, read, update, delete retailer order lists."""
import uuid
import logging

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, Field
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.api.deps import get_db, require_retailer
from app.api.v1.retailer import _get_or_create_retailer
from app.auth.models import CurrentUser
from app.models.ordering import IsbnList, IsbnListItem
from app.models.retailer import Retailer

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/isbn-lists", tags=["isbn-lists"])


# ─── Schemas ──────────────────────────────────────────────────────────────────

class IsbnListItemIn(BaseModel):
    isbn13: str = Field(min_length=13, max_length=13)
    quantity: int = Field(ge=1, default=1)
    note: str | None = None


class IsbnListCreate(BaseModel):
    name: str = Field(min_length=1, max_length=200)
    description: str | None = None
    items: list[IsbnListItemIn] = Field(default_factory=list)


class IsbnListUpdate(BaseModel):
    name: str | None = Field(default=None, min_length=1, max_length=200)
    description: str | None = None


class IsbnListItemOut(BaseModel):
    id: uuid.UUID
    isbn13: str
    quantity: int
    note: str | None
    added_at: str

    model_config = {"from_attributes": True}


class IsbnListOut(BaseModel):
    id: uuid.UUID
    name: str
    description: str | None
    item_count: int
    created_at: str
    updated_at: str

    model_config = {"from_attributes": True}


class IsbnListDetailOut(IsbnListOut):
    items: list[IsbnListItemOut]


class AddItemsRequest(BaseModel):
    items: list[IsbnListItemIn] = Field(..., min_length=1, max_length=500)


class RemoveItemsRequest(BaseModel):
    isbns: list[str] = Field(..., min_length=1, max_length=500)


# ─── Helpers ──────────────────────────────────────────────────────────────────

def _list_out(lst: IsbnList) -> IsbnListOut:
    return IsbnListOut(
        id=lst.id,
        name=lst.name,
        description=lst.description,
        item_count=len(lst.items),
        created_at=lst.created_at.isoformat(),
        updated_at=lst.updated_at.isoformat(),
    )


def _detail_out(lst: IsbnList) -> IsbnListDetailOut:
    return IsbnListDetailOut(
        id=lst.id,
        name=lst.name,
        description=lst.description,
        item_count=len(lst.items),
        created_at=lst.created_at.isoformat(),
        updated_at=lst.updated_at.isoformat(),
        items=[
            IsbnListItemOut(
                id=item.id,
                isbn13=item.isbn13,
                quantity=item.quantity,
                note=item.note,
                added_at=item.added_at.isoformat(),
            )
            for item in lst.items
        ],
    )


async def _get_list(db: AsyncSession, list_id: uuid.UUID, retailer: Retailer) -> IsbnList:
    lst = (
        await db.execute(
            select(IsbnList)
            .options(selectinload(IsbnList.items))
            .where(IsbnList.id == list_id, IsbnList.retailer_id == retailer.id)
        )
    ).scalar_one_or_none()
    if not lst:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="List not found")
    return lst


# ─── Endpoints ────────────────────────────────────────────────────────────────

@router.get("", response_model=list[IsbnListOut])
async def list_isbn_lists(
    db: AsyncSession = Depends(get_db),
    current_user: CurrentUser = Depends(require_retailer),
) -> list[IsbnListOut]:
    """Return all saved ISBN lists for the authenticated retailer."""
    retailer = await _get_or_create_retailer(db, current_user)
    rows = (
        await db.execute(
            select(IsbnList)
            .options(selectinload(IsbnList.items))
            .where(IsbnList.retailer_id == retailer.id)
            .order_by(IsbnList.updated_at.desc())
        )
    ).scalars().all()
    return [_list_out(r) for r in rows]


@router.post("", response_model=IsbnListDetailOut, status_code=status.HTTP_201_CREATED)
async def create_isbn_list(
    body: IsbnListCreate,
    db: AsyncSession = Depends(get_db),
    current_user: CurrentUser = Depends(require_retailer),
) -> IsbnListDetailOut:
    """Create a new saved ISBN list, optionally pre-populated with items."""
    retailer = await _get_or_create_retailer(db, current_user)
    lst = IsbnList(
        id=uuid.uuid4(),
        retailer_id=retailer.id,
        name=body.name,
        description=body.description,
    )
    db.add(lst)
    await db.flush()

    for item_in in body.items:
        db.add(IsbnListItem(
            id=uuid.uuid4(),
            list_id=lst.id,
            isbn13=item_in.isbn13,
            quantity=item_in.quantity,
            note=item_in.note,
        ))

    await db.commit()
    lst = await _get_list(db, lst.id, retailer)
    return _detail_out(lst)


@router.get("/{list_id}", response_model=IsbnListDetailOut)
async def get_isbn_list(
    list_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    current_user: CurrentUser = Depends(require_retailer),
) -> IsbnListDetailOut:
    """Return a saved list with all its items."""
    retailer = await _get_or_create_retailer(db, current_user)
    lst = await _get_list(db, list_id, retailer)
    return _detail_out(lst)


@router.patch("/{list_id}", response_model=IsbnListDetailOut)
async def update_isbn_list(
    list_id: uuid.UUID,
    body: IsbnListUpdate,
    db: AsyncSession = Depends(get_db),
    current_user: CurrentUser = Depends(require_retailer),
) -> IsbnListDetailOut:
    """Rename or update the description of a saved list."""
    retailer = await _get_or_create_retailer(db, current_user)
    lst = await _get_list(db, list_id, retailer)
    if body.name is not None:
        lst.name = body.name
    if body.description is not None:
        lst.description = body.description
    await db.commit()
    lst = await _get_list(db, list_id, retailer)
    return _detail_out(lst)


@router.delete("/{list_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_isbn_list(
    list_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    current_user: CurrentUser = Depends(require_retailer),
) -> None:
    """Delete a saved list and all its items."""
    retailer = await _get_or_create_retailer(db, current_user)
    lst = await _get_list(db, list_id, retailer)
    await db.delete(lst)
    await db.commit()


@router.post("/{list_id}/items", response_model=IsbnListDetailOut)
async def add_items_to_list(
    list_id: uuid.UUID,
    body: AddItemsRequest,
    db: AsyncSession = Depends(get_db),
    current_user: CurrentUser = Depends(require_retailer),
) -> IsbnListDetailOut:
    """Add ISBNs to a saved list. Increments quantity if ISBN already present."""
    retailer = await _get_or_create_retailer(db, current_user)
    lst = await _get_list(db, list_id, retailer)

    existing_map = {i.isbn13: i for i in lst.items}
    for item_in in body.items:
        if item_in.isbn13 in existing_map:
            existing_map[item_in.isbn13].quantity += item_in.quantity
        else:
            db.add(IsbnListItem(
                id=uuid.uuid4(),
                list_id=lst.id,
                isbn13=item_in.isbn13,
                quantity=item_in.quantity,
                note=item_in.note,
            ))

    await db.commit()
    lst = await _get_list(db, list_id, retailer)
    return _detail_out(lst)


@router.delete("/{list_id}/items", response_model=IsbnListDetailOut)
async def remove_items_from_list(
    list_id: uuid.UUID,
    body: RemoveItemsRequest,
    db: AsyncSession = Depends(get_db),
    current_user: CurrentUser = Depends(require_retailer),
) -> IsbnListDetailOut:
    """Remove specific ISBNs from a saved list."""
    retailer = await _get_or_create_retailer(db, current_user)
    lst = await _get_list(db, list_id, retailer)
    to_remove = {i for i in lst.items if i.isbn13 in body.isbns}
    for item in to_remove:
        await db.delete(item)
    await db.commit()
    lst = await _get_list(db, list_id, retailer)
    return _detail_out(lst)
