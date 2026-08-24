"""Router aggregatore per `/api/v1`."""

from fastapi import APIRouter

from price_service.api.v1 import prices

router = APIRouter(prefix="/api/v1")
router.include_router(prices.router)
