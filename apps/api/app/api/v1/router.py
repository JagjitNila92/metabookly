from fastapi import APIRouter
from app.api.v1 import (
    analytics, basket, books, catalog, distributor, onix, orders, portal, pricing, retailer, settings,
)

router = APIRouter(prefix="/api/v1")
router.include_router(catalog.router)
router.include_router(books.router)
router.include_router(pricing.router)
router.include_router(onix.router)
router.include_router(portal.router)
router.include_router(retailer.router)
router.include_router(settings.router)
router.include_router(distributor.router)
router.include_router(analytics.router)
router.include_router(basket.router)
router.include_router(orders.router)
