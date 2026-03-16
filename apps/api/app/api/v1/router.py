from fastapi import APIRouter
from app.api.v1 import catalog, books, pricing

router = APIRouter(prefix="/api/v1")
router.include_router(catalog.router)
router.include_router(books.router)
router.include_router(pricing.router)
