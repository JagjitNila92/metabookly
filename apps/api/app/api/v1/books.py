from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.api.deps import get_current_user
from app.auth.models import CurrentUser
from app.db.session import get_db
from app.models.book import Book
from app.schemas.book import BookDetail, ContributorOut, SubjectOut

router = APIRouter(prefix="/books", tags=["books"])


@router.get("/{isbn13}", response_model=BookDetail)
async def get_book(
    isbn13: str,
    db: AsyncSession = Depends(get_db),
    _: CurrentUser = Depends(get_current_user),
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
    return BookDetail.model_validate(book)


@router.get("/{isbn13}/contributors", response_model=list[ContributorOut])
async def get_contributors(
    isbn13: str,
    db: AsyncSession = Depends(get_db),
    _: CurrentUser = Depends(get_current_user),
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
    _: CurrentUser = Depends(get_current_user),
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
