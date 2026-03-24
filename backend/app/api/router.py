from fastapi import APIRouter
from .endpoints import auth, quotes, stock

router = APIRouter()

router.include_router(auth.router, prefix="/auth", tags=["auth"])
router.include_router(quotes.router, prefix="/quotes", tags=["quotes"])
router.include_router(stock.router, tags=["stock"])
