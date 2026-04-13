"""
ARC (Advance Reading Copy) public endpoints.

Anyone can request an ARC for a title that has arc_enabled=True.
Retailers are auto-identified from their Cognito token.
External requesters (trade press, bloggers) fill in the form manually.
"""
import asyncio
import logging
import uuid

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_db, get_optional_user
from app.auth.models import CurrentUser
from app.models.book import Book
from app.models.portal import FeedSource
from app.models.retailer import Retailer
from app.schemas.arc import ArcRequestCreate, ArcStatusOut
from app.services import arc_service
from app.services.email_service import send_arc_request_to_publisher

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/arc", tags=["arc"])


@router.post("/books/{isbn13}/request", status_code=201)
async def request_arc(
    isbn13: str,
    payload: ArcRequestCreate,
    db: AsyncSession = Depends(get_db),
    current_user: CurrentUser | None = Depends(get_optional_user),
) -> dict:
    """
    Submit an ARC request for a title.
    - Retailers: pass their token; name/email auto-filled from their profile if not provided.
    - Others: fill in name, email, type manually.
    """
    book = (await db.execute(select(Book).where(Book.isbn13 == isbn13))).scalar_one_or_none()
    if book is None:
        raise HTTPException(status_code=404, detail="Book not found")
    if not book.arc_enabled:
        raise HTTPException(status_code=409, detail="ARC requests are not available for this title")

    retailer_id: uuid.UUID | None = None
    if current_user and current_user.is_retailer:
        retailer = (await db.execute(
            select(Retailer).where(Retailer.cognito_sub == current_user.sub)
        )).scalar_one_or_none()
        if retailer:
            retailer_id = retailer.id

    try:
        arc = await arc_service.submit_arc_request(db, book, payload, retailer_id)
    except ValueError as e:
        raise HTTPException(status_code=409, detail=str(e))

    await db.commit()

    # Notify publisher — fire and forget
    publisher_name = "the publisher"
    publisher_email: str | None = None

    if arc.feed_source_id:
        fs = (await db.execute(
            select(FeedSource).where(FeedSource.id == arc.feed_source_id)
        )).scalar_one_or_none()
        if fs:
            publisher_name = fs.name
            publisher_email = fs.contact_email

    if publisher_email:
        asyncio.create_task(send_arc_request_to_publisher(
            publisher_email=publisher_email,
            publisher_name=publisher_name,
            book_title=book.title,
            isbn13=isbn13,
            requester_name=payload.requester_name,
            requester_email=str(payload.requester_email),
            requester_company=payload.requester_company,
            requester_type=payload.requester_type,
            requester_message=payload.requester_message,
        ))

    return {"id": str(arc.id), "status": "pending"}


@router.get("/books/{isbn13}/status", response_model=ArcStatusOut)
async def get_arc_status(
    isbn13: str,
    email: str,
    db: AsyncSession = Depends(get_db),
) -> ArcStatusOut:
    """
    Check whether a given email address has an existing ARC request for a title.
    Used by the frontend to show the correct CTA state.
    """
    book = (await db.execute(select(Book).where(Book.isbn13 == isbn13))).scalar_one_or_none()
    if book is None:
        raise HTTPException(status_code=404, detail="Book not found")

    result = await arc_service.get_requester_status(db, book.id, email, book.arc_s3_key)
    return ArcStatusOut(**result)
