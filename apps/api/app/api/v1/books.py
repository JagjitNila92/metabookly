import logging
from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.api.deps import get_db, get_optional_user
from app.auth.models import CurrentUser
from app.models.book import Book
from app.models.portal import BookViewEvent
from app.models.retailer import Retailer
from app.schemas.book import BookDetail, ContributorOut, SubjectOut

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/books", tags=["books"])


async def _log_view(
    db: AsyncSession,
    current_user: CurrentUser | None,
    book_id,
    isbn13: str,
) -> None:
    """Fire-and-forget: record who viewed which book."""
    try:
        retailer_id = None
        if current_user:
            retailer = (
                await db.execute(select(Retailer).where(Retailer.cognito_sub == current_user.sub))
            ).scalar_one_or_none()
            if retailer:
                retailer_id = retailer.id

        db.add(BookViewEvent(
            retailer_id=retailer_id,
            book_id=book_id,
            isbn13=isbn13,
            is_anonymous=retailer_id is None,
        ))
        await db.commit()
    except Exception as exc:
        logger.warning("Failed to log book view event: %s", exc)


@router.get("/{isbn13}", response_model=BookDetail)
async def get_book(
    isbn13: str,
    background_tasks: BackgroundTasks,
    db: AsyncSession = Depends(get_db),
    current_user: CurrentUser | None = Depends(get_optional_user),
) -> BookDetail:
    stmt = (
        select(Book)
        .options(
            selectinload(Book.publisher),
            selectinload(Book.contributors),
            selectinload(Book.subjects),
        )
        .where(Book.isbn13 == isbn13)
    )
    book = (await db.execute(stmt)).scalar_one_or_none()
    if not book:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Book not found")

    background_tasks.add_task(_log_view, db, current_user, book.id, isbn13)

    return BookDetail.model_validate(book)


@router.get("/{isbn13}/contributors", response_model=list[ContributorOut])
async def get_contributors(
    isbn13: str,
    db: AsyncSession = Depends(get_db),
) -> list[ContributorOut]:
    stmt = (
        select(Book)
        .options(selectinload(Book.contributors))
        .where(Book.isbn13 == isbn13)
    )
    book = (await db.execute(stmt)).scalar_one_or_none()
    if not book:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Book not found")
    return [ContributorOut.model_validate(c) for c in book.contributors]


@router.get("/{isbn13}/subjects", response_model=list[SubjectOut])
async def get_subjects(
    isbn13: str,
    db: AsyncSession = Depends(get_db),
) -> list[SubjectOut]:
    stmt = (
        select(Book)
        .options(selectinload(Book.subjects))
        .where(Book.isbn13 == isbn13)
    )
    book = (await db.execute(stmt)).scalar_one_or_none()
    if not book:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Book not found")
    return [SubjectOut.model_validate(s) for s in book.subjects]
